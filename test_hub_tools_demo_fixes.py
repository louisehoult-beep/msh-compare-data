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


LINE_SCRIPT = r"""
const fs = require('fs');
const A = process.argv.slice(-2);
const src = fs.readFileSync(A[0], 'utf8');
const blk = src.split('/* antimicrobial-line:start')[1].split('/* antimicrobial-line:end */')[0];
const f = new Function('/*' + blk + '; return lineAntimicrobial;')();
const lines = JSON.parse(A[1]);
process.stdout.write(JSON.stringify(lines.map(l => f({name: l[0], desc: l[1]}, ''))));
"""

# Runs the real comparison.js against the real data files with a stub browser,
# stops it once PRODUCTS is built, and reports every catalogue-backed product's
# antimicrobial line count. That is the grouping a member actually sees.
PRODUCTS_SCRIPT = r"""
const fs = require('fs'), path = require('path');
const root = process.argv[process.argv.length - 1];
let src = fs.readFileSync(path.join(root, 'app/comparison.js'), 'utf8');
const blk = src.split('/* antimicrobial-line:start')[1].split('/* antimicrobial-line:end */')[0];
const lineAM = new Function('/*' + blk + '; return lineAntimicrobial;')();
const marker = '    function kp(prod){';
if (src.indexOf(marker) === -1) { process.stderr.write('kp() marker gone'); process.exit(3); }
src = src.replace(marker, "globalThis.__P = PRODUCTS; globalThis.__D = detailFor; throw 'STOP';\n" + marker);
const anyEl = () => new Proxy(function(){}, {get: (t, k) => k === 'style' ? {} : anyEl(), set: () => true, apply: () => anyEl()});
globalThis.document = {getElementById: () => ({innerHTML: '', appendChild(){}}), createElement: () => anyEl()};
globalThis.fetch = (u) => { const rel = u.split('/main/')[1].split('?')[0];
  return Promise.resolve({json: () => Promise.resolve(JSON.parse(fs.readFileSync(path.join(root, rel), 'utf8')))}); };
eval(src);
let waited = 0;
(function poll(){
  if (!globalThis.__P) { if ((waited += 100) > 60000) { process.stderr.write('PRODUCTS never built'); process.exit(4); } return setTimeout(poll, 100); }
  const out = [];
  for (const p of globalThis.__P) {
    const d = globalThis.__D(p);
    if (!d || !d.items || !d.items.length) continue;
    out.push([p.supplier, p.name, d.items.filter(it => lineAM(it, p.name)).length, d.items.length]);
  }
  process.stdout.write(JSON.stringify(out));
})();
"""


class ComparisonAntimicrobial(unittest.TestCase):
    """Plain Atrauman was shown with an "Antimicrobial element" on a HARTMANN
    prospect's own product (30/09/2026): the attribute was read off every line
    a grouped search term returned, Atrauman AG's silver lines included. The
    element is now read one catalogue line at a time and a product carries it
    only when every line does."""

    LINES = [
        ["Atrauman", "Wound contact layer impregnated polymer dressing 7.5cm x 10cm", False],
        ["Atrauman silicone", "Wound contact layer silicone dressing two sided 7.5cm x 10cm", False],
        ["Atrauman AG", "Wound contact layer antimicrobial silver dressing 10cm x 20cm", True],
        ["Mepilex Ag", "Foam dressing antimicrobial silicone non bordered 15cmx15cm silver impregnated", True],
        ["Biatain Ag", "Foam dressing antimicrobial non bordered 10cm x 10cm", True],
        ["Inadine", "Wound contact layer antimicrobial iodine dressing 5cm x 5cm", True],
        ["Polymem Silver Adhesive", "Polymeric membrane dressing with surfactant Oval 3", True],
        # "silver" as a colour or a conductor is not an antimicrobial element
        ["Cochlear", "Cochlear Implant Sound Processor NUCLEUS 8 NEXA UNILATERAL PAEDIATRIC 8CM SILVER", False],
        ["Aesculap", "Surgical Instrument Accessories Reusable PRIMELINE PRO 3/4 LID SILVER", False],
        ["HI-Q", "Orthodontic Archwire - Stainless Steel Euro Upper .020in Bgt Silver", False],
        ["Philips", "ECG Monitoring Electrodes Wet Gel Electrode Disposable High performance snap Silver/silver chloride", False],
        ["Philips", "ECG Monitoring Electrodes Wet Gel Adult foam round silver sensor 54mm", False],
    ]

    @classmethod
    def setUpClass(cls):
        cls.node = shutil.which("node")
        cls.src = read("app/comparison.js")
        if not cls.node:
            return
        r = subprocess.run([cls.node, "-e", LINE_SCRIPT, os.path.join(HERE, "app", "comparison.js"),
                            json.dumps([l[:2] for l in cls.LINES])],
                           capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            raise RuntimeError("node line run failed: " + r.stderr)
        cls.line_res = json.loads(r.stdout)
        r = subprocess.run([cls.node, "-e", PRODUCTS_SCRIPT, HERE],
                           capture_output=True, text=True, timeout=180)
        if r.returncode != 0:
            raise RuntimeError("node product build failed: " + r.stderr)
        cls.products = {(s, n): (k, of) for s, n, k, of in json.loads(r.stdout)}

    def setUp(self):
        if not self.node:
            self.skipTest("node not installed; comparison.js not exercised")

    def test_each_line_read_on_its_own_words(self):
        for (name, desc, want), got in zip(self.LINES, self.line_res):
            self.assertEqual(got, want, "%s | %s" % (name, desc))

    def test_plain_atrauman_carries_no_antimicrobial_line(self):
        k, of = self.products[("Paul Hartmann (HARTMANN)", "Atrauman")]
        self.assertGreater(of, 0)
        self.assertEqual(k, 0, "plain Atrauman carries %d antimicrobial lines" % k)

    def test_atrauman_ag_still_does(self):
        k, of = self.products[("Paul Hartmann (HARTMANN)", "Atrauman AG")]
        self.assertGreater(of, 0)
        self.assertEqual(k, of)

    def test_product_level_claim_needs_every_line(self):
        self.assertIn("return productAttrs(d2.items, p.name);", self.src)
        self.assertNotIn("\\bsilver\\b/.test(txt)) a.silver = true", self.src)
        # a comparative claim ("theirs does not mention") only on a whole-product
        # yes, and only against an entry with no line stating it at all
        self.assertIn("myA0.silver === true && !shownAttr(theirA0, 'silver')", self.src)
        self.assertIn("theirA0.silver === true && !shownAttr(myA0, 'silver')", self.src)
        self.assertIn("myA0 && myA0.silver === true && theirA0 && !shownAttr(theirA0, 'silver')", self.src)


ATTRS_SCRIPT = r"""
const fs = require('fs');
const A = process.argv.slice(-2);
const src = fs.readFileSync(A[0], 'utf8');
const b1 = src.split('/* antimicrobial-line:start')[1].split('/* antimicrobial-line:end */')[0];
const b2 = src.split('/* catalogue-attrs:start')[1].split('/* catalogue-attrs:end */')[0];
const F = new Function('/*' + b1 + '/*' + b2 + '; return {lineAttrs, productAttrs, shownAttr};')();
const q = JSON.parse(A[1]);
const out = {lines: q.lines.map(l => F.lineAttrs({name: l[0], desc: l[1]}, '')),
             products: q.products.map(ls => { const a = F.productAttrs(ls.map(l => ({name: l[0], desc: l[1]})), '');
               const shown = {}; ['material','form','reg','latex','silver','bloodctl','needlefree','tint','dehp','dehpfree']
                 .forEach(k => { const v = F.shownAttr(a, k); if (v !== null) shown[k] = v; });
               return {whole: Object.fromEntries(Object.entries(a).filter(([k]) => k !== 'part' && k !== 'packs')), shown}; })};
process.stdout.write(JSON.stringify(out));
"""


class ComparisonCatalogueAttributes(unittest.TestCase):
    """The whole-product rule applied to every attribute in the aligned table
    (30/09/2026), and the non-attribute readings that were live: "powder free"
    read as a powder, "non-latex" as latex, "DEHP-free" as DEHP present,
    "prothrombin time" as a biologic, "adhesive border" as a sealant."""

    LINES = [
        # [name, desc, attribute, expected value or None]
        ["Gammex Non-Latex", "Surgeons gloves synthetic latex free powder free sterile", "form", None],
        ["Gammex Non-Latex PI", "Surgeons gloves polyisoprene sterile", "latex", "latex-free"],
        ["Gammex Latex", "Surgeons gloves latex powder free sterile", "latex", "natural rubber latex"],
        ["Alaris", "Infusion set 3mm id dehp-free pvc", "dehp", None],
        ["Alaris", "Infusion set 3mm id dehp-free pvc", "dehpfree", True],
        ["Unoquip", "Urine meter hanger straps dehp/phthalate-free latex free", "dehp", None],
        ["Codan", "Gravity solution set no dehp tubing", "dehp", None],
        ["Polymed", "Extension set rotating luer non- dehp tubing", "dehp", None],
        ["Surflo", "Metal needle winged device with extension 30cm tube dehp", "dehp", True],
        ["CoaguChek", "Prothrombin time test strips", "material", None],
        ["Surgiflo", "Haemostat flowable haemostatic matrix (without thrombin)", "material", None],
        ["Surgiflo", "Haemostat flowable matrix with thrombin", "material", "biologic (fibrin/thrombin)"],
        ["ActivHeal", "Foam dressing silicone including adhesive border 10cm x 10cm", "form", None],
        ["ChloraPrep", "Skin disinfectant medicinal product 26ml sterile applicator 2% chlorhexidine", "form", None],
        ["ChloraPrep", "Skin disinfectant medicinal product 26ml sterile applicator 2% chlorhexidine", "reg", "a licensed medicinal product"],
        ["Floseal", "Haemostat product laparoscopic applicator", "form", "flowable matrix (applicator)"],
        ["Prevantics", "Brush scrub pre operative integral sponge iodine and nail pick", "form", None],
        ["Gown", "Surgical gown medium sterile sms and knitted cuffs", "form", None],
        ["Surgicel Nu-Knit", "Haemostatic fabrics 75 x 100mm", "form", "knitted fabric"],
        ["Nexiva", "Closed IV catheter 20g x 32mm with blood control technology", "bloodctl", True],
    ]

    PRODUCTS = [
        # every line: whole-product value
        [["X", "IV cannula 20g with blood control"], ["X", "IV cannula 22g with blood control"]],
        # some lines: never whole, says how many
        [["X", "IV cannula 20g with blood control"], ["X", "IV cannula 22g"], ["X", "IV cannula 24g"]],
        # lines disagree: says so, never picks one
        [["S", "Haemostat absorbable gelatin porcine 1g"], ["S", "Haemostat absorbable gelatin 80 x 30mm"]],
    ]

    @classmethod
    def setUpClass(cls):
        cls.node = shutil.which("node")
        if not cls.node:
            return
        q = {"lines": [l[:2] for l in cls.LINES], "products": cls.PRODUCTS}
        r = subprocess.run([cls.node, "-e", ATTRS_SCRIPT, os.path.join(HERE, "app", "comparison.js"),
                            json.dumps(q)], capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            raise RuntimeError("node attrs run failed: " + r.stderr)
        cls.res = json.loads(r.stdout)

    def setUp(self):
        if not self.node:
            self.skipTest("node not installed; comparison.js not exercised")

    def test_each_line_read_in_its_attribute_sense_only(self):
        for (name, desc, key, want), got in zip(self.LINES, self.res["lines"]):
            self.assertEqual(got.get(key), want, "%s | %s -> %s" % (name, desc, key))

    def test_every_line_gives_a_whole_product_value(self):
        p = self.res["products"][0]
        self.assertIs(p["whole"].get("bloodctl"), True)
        self.assertIs(p["shown"].get("bloodctl"), True)

    def test_some_lines_never_become_the_product(self):
        p = self.res["products"][1]
        self.assertNotIn("bloodctl", p["whole"])
        self.assertEqual(p["shown"]["bloodctl"], "Stated on 1 of 3 catalogue pack lines only")

    def test_disagreeing_lines_are_reported_not_resolved(self):
        p = self.res["products"][2]
        self.assertNotIn("material", p["whole"])
        self.assertEqual(p["shown"]["material"], "varies by pack line: porcine gelatin (1), gelatin (1)")
        self.assertEqual(p["whole"].get("form"), None)

    def test_does_not_mention_claims_need_whole_product_and_silence(self):
        src = read("app/comparison.js")
        for k in ("bloodctl", "needlefree", "tint", "silver"):
            self.assertIn("myA0.%s === true && !shownAttr(theirA0, '%s')" % (k, k), src)
        for k in ("bloodctl", "tint", "silver", "dehp"):
            self.assertIn("theirA0.%s === true && !shownAttr(myA0, '%s')" % (k, k), src)
        # a partly-stated range is never a like-for-like swap
        self.assertIn("if (myA0.part[ks[q]] || pa.part[ks[q]]) return false;", src)


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



class CompanyReportNeverHiddenByScrollReveal(unittest.TestCase):
    """30/09/2026: every report body rendered blank for members. The site-wide
    scroll-reveal snippet (WPCode 3108) tagged the whole .mcr-body, ~47,000px
    tall, with .rv (opacity 0); its IntersectionObserver needs 5% of the
    element on screen, ~2,350px, which no viewport shows, so it never
    revealed. The report opts out in CSS and marks itself revealed in JS."""

    def setUp(self):
        self.src = read("app/company-report.js")

    def test_css_opt_out_covers_inside_self_and_host(self):
        self.assertIn(
            "'.rv-on .mcr .rv,.rv-on .mcr.rv,.rv-on .rv:has(.mcr)"
            "{opacity:1!important;transform:none!important;transition:none!important;}'",
            self.src)

    def test_opt_out_is_not_inside_a_media_query(self):
        i = self.src.index("'.rv-on .mcr .rv,")
        before = self.src[:i]
        opens = before.count("'@media")
        # every @media block opened before the rule has been closed by a lone '}'
        self.assertEqual(opens, before.count("\n    '}',"))

    def test_js_marks_report_revealed_after_render_and_at_load(self):
        self.assertIn("function unhideFromReveal(root) {", self.src)
        self.assertIn("if (s) groupClosedPanels(result);\n      unhideFromReveal(result);", self.src)
        self.assertIn("window.addEventListener('load', function () { unhideFromReveal(result); });", self.src)

    def test_no_mutation_observer_loop(self):
        self.assertNotIn("new MutationObserver(", self.src)


if __name__ == "__main__":
    unittest.main(verbosity=2)
