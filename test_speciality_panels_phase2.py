#!/usr/bin/env python3
"""Speciality panels phase 2 (29/09/2026): directory-tagged suppliers and the
other-framework note, GP prescribing, MHRA Drug Safety Updates, Drug Tariff Part
VIIIA, and counts in rule text computed at build time.

Stdlib only. Builds panels IN MEMORY through build_speciality_panels.load_sources()
and build(); it never writes data/speciality-panels/, so it cannot dirty a clone the
way test_speciality_panels.py does.

  python3 test_speciality_panels_phase2.py
"""
import json
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "scripts"))
os.chdir(HERE)
import build_speciality_panels as B  # noqa: E402
import refresh_drug_tariff_part_viiia as V  # noqa: E402

_SOURCES = None


def read(*parts):
    with open(os.path.join(HERE, *parts), encoding="utf-8") as fh:
        return fh.read()


def sources():
    global _SOURCES
    if _SOURCES is None:
        _SOURCES = B.load_sources()
    return _SOURCES


_PANELS = {}


def panel(slug):
    if slug not in _PANELS:
        _PANELS[slug] = B.build(slug, sources())
    return _PANELS[slug]


class DirectoryTaggedSuppliers(unittest.TestCase):

    def test_ego_is_listed_on_dermatology(self):
        """The case that started this: a paying member works at Ego (QV, Sunsense),
        and before 29/09/2026 the dermatology Suppliers tab never named it."""
        d = panel("dermatology")
        names = [s["name"] for s in d["directorySuppliers"]]
        self.assertIn("Ego Pharmaceuticals UK", names)
        ego = next(s for s in d["directorySuppliers"] if s["name"] == "Ego Pharmaceuticals UK")
        self.assertEqual(ego["provenance"], "directory-tagged")
        self.assertTrue(ego["seedLabels"])

    def test_framework_named_list_is_unchanged_and_labelled(self):
        """Directory tags never leak into the framework-named list or its count."""
        d = panel("tissue-viability-and-wound-care")
        self.assertTrue(d["suppliers"])
        self.assertTrue(all(s["provenance"] == "framework-named" for s in d["suppliers"]))
        self.assertEqual(d["counts"]["suppliers"], len(d["suppliers"]))
        fw_names = {s["name"] for s in d["suppliers"]}
        self.assertFalse(fw_names & {s["name"] for s in d["directorySuppliers"]},
                         "a company must be listed once, not in both lists")
        self.assertEqual(d["counts"]["suppliersDirectoryTagged"], len(d["directorySuppliers"]))

    def test_other_framework_note_synthetic(self):
        """Lou's rule, 29/09/2026: a tagged supplier on a framework NOT counted for this
        speciality is still listed, with that framework named and linked."""
        src = dict(sources())
        src["cache"] = {}
        src["frameworks"] = {"frameworks": [
            {"name": "Zeta Counted Framework", "url": "https://example.invalid/own",
             "suppliers": ["Acme Own Ltd"]},
            {"name": "Omega Other Framework", "url": "https://example.invalid/other",
             "reference": "2099/S 000-000001", "ends": "1 January 2099",
             "suppliers": ["Qwertyuiop Dermacorp Limited"]},
        ]}
        src["seed"] = [{"name": "Qwertyuiop Dermacorp Limited",
                        "specialities": ["Dermatology / skin"],
                        "frameworks": ["NHS SBS — SBS99999"]}]
        own = [{"name": "Zeta Counted Framework", "suppliers": ["Acme Own Ltd"]}]
        rows, _tagged = B.build_directory_suppliers("dermatology", own, [], src)
        self.assertEqual(len(rows), 1)
        r = rows[0]
        self.assertEqual([o["name"] for o in r["otherFrameworks"]], ["Omega Other Framework"])
        self.assertEqual(r["otherFrameworks"][0]["url"], "https://example.invalid/other")
        self.assertIn("Omega Other Framework", r["frameworkNote"])
        self.assertIn("not counted as this speciality's", r["frameworkNote"])
        self.assertEqual([x["name"] for x in r["directoryFrameworks"]], ["NHS SBS — SBS99999"])
        self.assertIn("SBS99999", r["frameworkNote"])

    def test_own_framework_is_never_an_other_framework(self):
        src = dict(sources())
        src["cache"] = {}
        src["frameworks"] = {"frameworks": [
            {"name": "Zeta Counted Framework", "url": "u", "suppliers": ["Qwertyuiop Dermacorp Limited"]}]}
        src["seed"] = [{"name": "Qwertyuiop Dermacorp Limited", "specialities": ["Dermatology / skin"]}]
        fw = [{"name": "Zeta Counted Framework", "suppliers": ["Qwertyuiop Dermacorp Limited"]}]
        sup = B.build_suppliers(fw, src["registry"])
        rows, tagged = B.build_directory_suppliers("dermatology", fw, sup, src)
        self.assertEqual(rows, [], "a framework-named company is not repeated as directory-tagged")
        self.assertTrue(tagged)

    def test_real_other_framework_note_carries_a_link(self):
        d = panel("dermatology")
        noted = [s for s in d["directorySuppliers"] if s["otherFrameworks"]]
        self.assertTrue(noted, "at least one dermatology-tagged company is on another framework")
        for s in noted:
            self.assertTrue(s["frameworkNote"])
            for o in s["otherFrameworks"]:
                self.assertTrue((o.get("url") or "").startswith("https://www.supplychain.nhs.uk/"), o)

    def test_page_with_no_mapped_label_says_so(self):
        d = panel("stroke")
        self.assertEqual(d["directorySuppliers"], [])
        self.assertIn("No supplier directory label maps", d["rules"]["directorySuppliers"])


class ComputedCounts(unittest.TestCase):

    def test_number_words(self):
        self.assertEqual(B.number_word(13), "thirteen")
        self.assertEqual(B.number_word(17), "seventeen")
        self.assertEqual(B.number_word(42), "forty-two")
        self.assertEqual(B.number_word(1474), "1,474")

    def test_dermatology_award_count_is_computed(self):
        """The 'thirteen' bug: the rule text must carry the current matched total."""
        d = panel("dermatology")
        n = d["counts"]["awardsMatched"]
        text = d["rules"]["frameworks"]
        self.assertIn("of the %s matched notices" % B.number_word(n), text)
        self.assertNotIn("Nine of the thirteen", text)
        self.assertNotIn("all thirteen", text)

    def test_no_token_survives_in_any_panel(self):
        for slug in B.SPECIALITY_RULES:
            d = panel(slug)
            blob = json.dumps(d.get("rules") or {})
            self.assertNotIn("[[", blob, slug)

    def test_unknown_token_stops_the_build(self):
        ctx = {"slug": "x", "awards": [], "frameworks": [], "suppliers": []}
        with self.assertRaises(SystemExit):
            B.render_counts("[[noSuchCount]]", ctx)

    def test_framework_that_moved_stops_the_build(self):
        ctx = {"slug": "x", "frameworks": [], "fw_doc": {"frameworks": []}, "awards": []}
        with self.assertRaises(SystemExit):
            B.render_counts("[[fwListed:A Framework That Is Not There]]", ctx)

    def test_arithmetic_and_formats(self):
        ctx = {"slug": "x", "awards": [{"title": "Community Dermatology Service"},
                                       {"title": "Dermatoscopes"}],
               "frameworks": [], "suppliers": [{"resolved": True}] * 25}
        self.assertEqual(B.render_counts("[[suppliers]] for [[suppliers-1]]", ctx), "25 for 24")
        self.assertEqual(B.render_counts("[[awardsTitle:service|Word]] of [[awards|word]]", ctx),
                         "One of two")

    def test_absent_framework_check(self):
        rule = {"absentFrameworks": ("Blood Draw Tools",)}
        B.check_absent_frameworks("x", rule, {"frameworks": [{"name": "Something Else"}]})
        with self.assertRaises(SystemExit):
            B.check_absent_frameworks("x", rule, {"frameworks": [{"name": "Blood Draw Tools and Accessories"}]})

    def test_sweep_left_no_typed_panel_counts(self):
        """Phrases removed by the 29/09/2026 sweep must not come back as typed text."""
        src = read("scripts", "build_speciality_panels.py")
        for bad in ["Nine of the thirteen", "Four of the fifteen", "56 of the 81",
                    "twenty thousand appliance lines", "582 of its 645",
                    "reads 26 where 25", "shows 25 entries for 24",
                    "which the Hub does not hold", "no part of the Drug Tariff in this dataset"]:
            code = "\n".join(l for l in src.splitlines() if not l.strip().startswith("#"))
            self.assertNotIn(bad, code, bad)


class GPPrescribing(unittest.TestCase):

    def test_dermatology_emollients_include_2122_and_reconcile(self):
        d = panel("dermatology")
        gp = d["gpPrescribing"]
        self.assertTrue(gp["defined"])
        m = next(x for x in gp["markets"] if x["id"] == "emollients")
        self.assertIn("21.22", m["bnf"])
        ix = sources()["gp"].index
        s2122 = ix["sectionTotals"]["2122"]["i"][-1]
        s1302 = sources()["gp"].shard("1302")
        em1302 = sum(arr[-1] or 0 for code, sub in s1302["s"].items() if code.startswith("130201")
                     for by_key in sub["t"].values() for arr in by_key.values())
        self.assertEqual(m["items"], int(round(s2122 + em1302)))
        self.assertGreater(s2122, 0)

    def test_brand_share_is_ordered_and_bounded(self):
        m = panel("dermatology")["gpPrescribing"]["markets"][0]
        items = [t["items"] for t in m["topNational"]]
        self.assertEqual(items, sorted(items, reverse=True))
        self.assertLessEqual(sum(t["share"] for t in m["topNational"]), 100.0 + 1e-6)
        self.assertEqual(len(m["icbLeaders"]), len([c for c in sources()["gp"].index["icbs"] if c != "-"]))
        for icb in m["icbLeaders"]:
            self.assertNotIn("INTEGRATED CARE BOARD", icb["name"])

    def test_trend_floor_is_respected(self):
        m = panel("dermatology")["gpPrescribing"]["markets"][0]
        floor = sources()["gp"].index["minBaselineItems"]
        self.assertIsNone(B._pct(10, floor - 1, floor))
        self.assertIsNotNone(B._pct(10, floor, floor))
        self.assertTrue(all(t["yoy"] is None or isinstance(t["yoy"], float) for t in m["topNational"]))

    def test_unmapped_speciality_is_honest(self):
        gp = panel("stroke")["gpPrescribing"]
        self.assertFalse(gp["defined"])
        self.assertTrue(gp["whyEmpty"])


class MarketShare(unittest.TestCase):
    """30/09/2026: dermatology's Market Intelligence gets the computed primary care,
    secondary care and Drug Tariff breakdown that wound care only had by hand."""

    def test_dermatology_has_all_three_views(self):
        ms = panel("dermatology").get("marketShare")
        self.assertTrue(ms and ms["markets"])
        m = ms["markets"][0]
        self.assertEqual(m["id"], "emollients")
        self.assertIn("21.22", m["bnf"])
        self.assertTrue(m["primary"]["brands"])
        self.assertTrue(m["secondary"] and m["secondary"]["brands"])
        self.assertTrue(m["tariff"] and m["tariff"]["topSuppliers"])

    def test_primary_total_is_the_gp_market_total(self):
        d = panel("dermatology")
        m = d["marketShare"]["markets"][0]["primary"]
        g = next(x for x in d["gpPrescribing"]["markets"] if x["id"] == "emollients")
        self.assertEqual(m["items"], g["items"])
        listed = sum(b["items"] for b in m["brands"]) + m["otherBrands"]["items"]
        self.assertLessEqual(abs(listed - m["items"]), 1)

    def test_qv_is_one_brand_of_three_products_with_icbs(self):
        m = panel("dermatology")["marketShare"]["markets"][0]["primary"]
        qv = [b for b in m["brands"] if b["brand"] == "QV"]
        self.assertEqual(len(qv), 1)
        self.assertEqual(len(qv[0]["products"]), len(set(qv[0]["products"])))
        self.assertTrue(all(p.startswith("QV") for p in qv[0]["products"]))
        self.assertTrue(qv[0]["topIcbs"])
        for ic in qv[0]["topIcbs"]:
            self.assertGreater(ic["items"], 0)
            self.assertTrue(0 < ic["shareOfIcb"] <= 100)

    def test_brand_key_rules(self):
        self.assertEqual(B.brand_key("QV Gentle wash", False)[1], "QV")
        self.assertEqual(B.brand_key("QV cream", False)[0], B.brand_key("QV Intensive ointment", False)[0])
        self.assertNotEqual(B.brand_key("Aqueous cream (Zuche Pharmaceuticals Ltd)", False)[0],
                            B.brand_key("Aqueous cream (Other Ltd)", False)[0])
        self.assertEqual(B.brand_key("Urea", True)[0], "__generic__")
        self.assertEqual(B.brand_key("E45 cream", False)[1], "E45")

    def test_appliance_markets_have_the_block(self):
        """30/09/2026, Lou: the same block for stoma, continence, diabetes technology
        and wound dressings. Each Drug Tariff view is built from the market's own BNF
        codes, never from the panel's wider Part IX slice."""
        want = {"colorectal-gi-and-endoscopy": ["stoma-bags"],
                "continence-bladder-and-bowel": ["catheters"],
                "diabetes-and-endocrinology": ["sensors", "bg-strips"],
                "tissue-viability-and-wound-care": ["dressings"]}
        dt = sources()["drug_tariff"]
        ix = {k: i for i, k in enumerate(dt["schema"])}
        for slug, ids in want.items():
            d = panel(slug)
            ms = d.get("marketShare")
            self.assertEqual([m["id"] for m in ms["markets"]], ids, slug)
            for m in ms["markets"]:
                self.assertTrue(m["primary"]["brands"], (slug, m["id"]))
                mk = next(x for x in B.GP_MARKETS[slug] if x["id"] == m["id"])
                n = sum(1 for r in dt["rows"] if (r[ix["bnf"]] or "").startswith(tuple(mk["prefixes"])))
                self.assertEqual(m["tariff"]["lineCount"], n, (slug, m["id"]))
            # share-only markets feed the block, not the GP prescribing sizing
            gp_ids = [x["id"] for x in d["gpPrescribing"]["markets"]]
            for mk in B.GP_MARKETS[slug]:
                if mk.get("shareOnly"):
                    self.assertNotIn(mk["id"], gp_ids)

    def test_unmarked_speciality_has_no_block(self):
        self.assertNotIn("marketShare", panel("respiratory"))

    def test_renderer_has_the_market_mount(self):
        js = read("app", "speciality-panels.js")
        self.assertIn("msh-spec-market", js)
        self.assertIn("d.marketShare", js)


class MhraDsu(unittest.TestCase):

    def test_dermatology_slice_matches_the_feed(self):
        d = panel("dermatology")["mhraDsu"]
        doc = sources()["mhra_dsu"]
        want = [u for u in doc["updates"] if "dermatology" in u["specialities"] and not u.get("roundup")]
        self.assertEqual(d["count"], len(want))
        self.assertEqual([u["url"] for u in d["updates"]], [u["url"] for u in want[:len(d["updates"])]])
        self.assertFalse(d["noFacet"])

    def test_no_facet_speciality_says_so_rather_than_showing_empty(self):
        doc = sources()["mhra_dsu"]
        slug = doc["panelsWithNoFacet"][0]
        d = panel(slug)["mhraDsu"]
        self.assertTrue(d["noFacet"])
        self.assertIn("does not tag", d["whyEmpty"])
        self.assertEqual(d["updates"], [])
        self.assertIn("does not tag", panel(slug)["rules"]["mhraDsu"])


class TariffViiia(unittest.TestCase):

    def test_dermatology_lines_are_classified_by_bnf(self):
        v = panel("dermatology")["drugTariffViiia"]
        self.assertTrue(v["lineCount"] > 0)
        self.assertTrue(all((ln["bnf"] or "").startswith("13") for ln in v["lines"]))
        self.assertEqual(sum(v["categoryCounts"].values()), v["lineCount"])

    def test_prefixes_are_not_redundant(self):
        self.assertEqual(B.viiia_prefixes("dermatology"), ["13"])

    def test_attach_bnf_carries_forward_on_failure(self):
        doc = {"rows": [["A", "1", "t", "M", 100, "111"], ["B", "1", "t", "C", 200, "222"]]}
        prior = {"bnfBySnomed": {"111": "1302011A0AAAAAA"}}

        def broken(_codes):
            raise RuntimeError("offline")
        V.attach_bnf(doc, prior, mapper=broken)
        self.assertEqual(doc["bnfBySnomed"], {"111": "1302011A0AAAAAA"})
        self.assertEqual(doc["bnfUnmapped"], 1)
        self.assertIn("carried forward", doc["bnfMapNote"])

    def test_bnf_map_picks_the_code_with_most_items(self):
        def fake_sql(_t, _q):
            return [{"s": "111", "b": "X", "i": "5"}, {"s": "111", "b": "Y", "i": "9"}]
        m, tables = V.bnf_map(["111"], run_sql=fake_sql, resources=lambda: [("202607", "T")])
        self.assertEqual(m, {"111": "Y"})
        self.assertEqual(tables, ["T"])


class WorksAreNotSpecialityAwards(unittest.TestCase):
    """Lou, 29/09/2026: building and estates works are not a speciality award."""

    def test_diabetes_alterations_is_gone(self):
        titles = [a["title"] for a in panel("diabetes-and-endocrinology")["awards"]]
        self.assertNotIn("Alterations to Diabetes Centre", titles)

    def test_the_class_not_the_title(self):
        W = B.is_works_award
        self.assertTrue(W({"title": "Alterations to Diabetes Centre", "supplier": "AD ARCHITECTS LIMITED"}))
        self.assertTrue(W({"title": "NGH - Maternity Bereavement Suite", "supplier": "J.E.T. Construction (MK) Ltd",
                           "cpv": ["45453100"]}))
        self.assertTrue(W({"title": "Mental Health Emergency Department (MH ED)", "cpv": ["45215100", "45453000"]}))
        self.assertTrue(W({"title": "Pharmacy Boiler Replacement", "cpv": ["45000000"]}))
        # Equipment the buyer filed under a works CPV stays.
        self.assertFalse(W({"title": "Mold Community Hospital X-Ray Room Replacement", "cpv": ["45000000"]}))
        self.assertFalse(W({"title": "Ultrasound refit", "supplier": "PHILIPS ELECTRONICS UK LIMITED", "cpv": ["45210000"]}))
        self.assertFalse(W({"title": "CVH - Macerators plus Maintenance for 2 Years", "cpv": ["45330000"]}))
        self.assertFalse(W({"title": "Fluoroscopy Unit and Associated Enabling Works",
                            "supplier": "Siemens Healthcare Limited"}))
        # One builder among several winners does not make an equipment service works.
        self.assertFalse(W({"title": "Integrated Community Equipment Services & Minor Adaptations Services",
                            "supplier": "MEDEQUIP ASSISTIVE TECHNOLOGY LIMITED, SRD BUILDING SERVICES LTD",
                            "cpv": ["33190000", "50000000"]}))
        # A decontamination engineering service (CPV 71315200) is not architecture.
        self.assertFalse(W({"title": "Authorising Engineer (AE) - Decontamination", "cpv": ["71315200"]}))

    def test_estates_pages_are_exempt(self):
        self.assertTrue(B.SPECIALITY_RULES["capital-estates-watch"].get("worksAreThePatch"))
        est = [a["title"] for a in B.matched_awards(
            B.compile_rule(B.SPECIALITY_RULES["capital-estates-watch"]),
            B.SPECIALITY_RULES["capital-estates-watch"], sources()["tender_history"],
            sources()["framework_awards"])]
        self.assertTrue(any(B.is_works_award({"title": t}) for t in est))

    def test_no_works_row_on_any_clinical_panel(self):
        for slug, rule in B.SPECIALITY_RULES.items():
            if rule.get("worksAreThePatch"):
                continue
            for a in panel(slug)["awards"]:
                self.assertFalse(B.is_works_award(a), (slug, a["title"]))


class MoneyHasAPoundSign(unittest.TestCase):

    def test_nutrition_and_obesity_print_pounds(self):
        self.assertIn("\u00a3638.2m", panel("nutrition-and-dietetics")["rules"]["frameworks"])
        self.assertIn("\u00a389m", panel("nutrition-and-dietetics")["rules"]["frameworks"])
        self.assertIn("\u00a3574,302,390", panel("obesity-and-weight-management")["rules"]["frameworks"])

    def test_guard_stops_bare_money(self):
        for bad in ["prescribing: 638.2m of net ingredient cost", "worth 89m over its term",
                    "accounted for 574,302,390 of net ingredient cost", "priced at $12"]:
            with self.assertRaises(SystemExit, msg=bad):
                B.check_money("x", {"frameworks": bad})
        B.check_money("x", {"frameworks": "\u00a3638.2m of net ingredient cost; 3,064,223 items; 51 suppliers"})

    def test_every_panel_passes_the_guard(self):
        for slug in B.SPECIALITY_RULES:
            B.check_money(slug, panel(slug)["rules"])


class LoaderAndWorkflow(unittest.TestCase):

    def test_renderer_reads_every_new_section(self):
        """The data and its loader are two halves: every new key must be read by the JS."""
        js = read("app", "speciality-panels.js")
        for key in ["directorySuppliers", "gpPrescribing", "mhraDsu", "drugTariffViiia",
                    "otherFrameworks", "directoryFrameworks"]:
            self.assertIn(key, js, key)

    def test_panels_workflow_commits_local_intel_lastcheck(self):
        yml = read(".github", "workflows", "speciality-panels.yml")
        self.assertTrue(re.search(r"git add data/speciality-panels/ data/speciality-local-intel\.json", yml))


if __name__ == "__main__":
    unittest.main(verbosity=1)
