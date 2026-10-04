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
import re
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



# ---------------------------------------------------------------------------
# Member-visible text found on a live QA of the Essity and HARTMANN reports,
# 30/09/2026: curator notes printed under Company information, an advice
# sentence closing a summary, two "Website" pills, and internal file names in
# method text. Each class below holds one of those fixes in place.
# ---------------------------------------------------------------------------
import re

# The markers the QA named, plus the Cowork-OS ones the same sweep found.
INTERNAL = re.compile(
    r"merge_duplicates|\bLou(?:'s)?\b|02-Elevate-and-Thrive|Identity Decision Pack"
    r"|\b[Cc]urator|\bTODO\b|\^o\d+|E&T client|alias-overlay"
    r"|(?<![/\w])[\w\-]+(?:/[\w\-]+)*\.(?:json|md|py|toml)\b")
# A path on a company's own public site ("/collections/all/products.json") is a
# cited source, not an internal file, so a leading "/" is allowed above.


def load(rel):
    with open(os.path.join(HERE, rel), encoding="utf-8") as f:
        return json.load(f)


def block(src, start, end):
    return src.split(start)[1].split(end)[0]


NODE_EVAL = r"""
const fs = require('fs');
const A = process.argv.slice(-3);
const src = fs.readFileSync(A[0], 'utf8');
const [start, end, fn] = JSON.parse(A[1]);
const blk = src.split(start)[1].split(end)[0];
const f = new Function('/*' + blk + '; return ' + fn + ';')();
const args = JSON.parse(fs.readFileSync(A[2], 'utf8'));
process.stdout.write(JSON.stringify(args.map(a => f.apply(null, a))));
"""


def node_map(start, end, fn, arglists):
    node = shutil.which("node")
    if not node:
        raise unittest.SkipTest("node not installed; renderer block not exercised")
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as t:
        json.dump(arglists, t)
        tmp = t.name
    try:
        r = subprocess.run([node, "-e", NODE_EVAL, os.path.join(HERE, "app", "company-report.js"),
                            json.dumps([start, end, fn]), tmp],
                           capture_output=True, text=True, timeout=120)
    finally:
        os.unlink(tmp)
    if r.returncode != 0:
        raise RuntimeError("node run failed: " + r.stderr)
    return json.loads(r.stdout)


def all_suppliers():
    """Every supplier the report can open: index merged with seed, seed wins."""
    seed = {s["name"]: s for s in load("data/supplier-seed.json")["suppliers"]}
    out = {}
    for s in load("data/supplier-index.json")["suppliers"]:
        out[s["name"]] = seed.get(s["name"], s)
    for n, s in seed.items():
        out.setdefault(n, s)
    return out


class CompanyReportNeverRendersCuratorNotes(unittest.TestCase):
    """`note` is the curators' working record. A note carrying an internal
    marker is not rendered; the Essity note was the one found live."""

    @classmethod
    def setUpClass(cls):
        cls.sup = all_suppliers()
        cls.names = [n for n, s in cls.sup.items() if s.get("note")]
        cls.out = dict(zip(cls.names, node_map(
            "/* member-text:start", "/* member-text:end */", "memberNote",
            [[cls.sup[n]["note"]] for n in cls.names])))

    def test_essity_note_is_not_rendered(self):
        self.assertTrue(self.sup["Essity UK Limited"]["note"])
        self.assertEqual(self.out["Essity UK Limited"], "")

    def test_no_rendered_note_carries_an_internal_marker(self):
        leaks = [n for n, t in self.out.items() if t and INTERNAL.search(t)]
        self.assertEqual(leaks, [], "notes that would render internal text: %s" % leaks[:10])

    def test_a_plain_note_still_renders(self):
        job = re.compile(r"\b[a-z]+(?:-[a-z]+){2,} (?:run|routine)\b|[Cc]loud routine")
        plain = [n for n in self.names
                 if not INTERNAL.search(self.sup[n]["note"]) and not job.search(self.sup[n]["note"])]
        self.assertGreater(len(plain), 800)
        for n in plain:
            self.assertEqual(self.out[n], self.sup[n]["note"].strip(), n)

    def test_both_note_sites_go_through_the_gate(self):
        src = read("app/company-report.js")
        self.assertNotIn("esc(sub.note)", src)
        self.assertNotIn("esc(s.note)", src)
        self.assertEqual(src.count("esc(memberNote("), 2)


class CompanyReportSummariesAreInformationNotAdvice(unittest.TestCase):
    """HUB-VERIFICATION-STANDARD rule 14: the summary (deepDive.lede) states
    facts; it never tells the reader what to do."""

    ADVICE = re.compile(
        r"\byou should\b|\bwe recommend\b|\bmake sure\b|\bour advice\b"
        r"|\b(?:A|An|Any|Anyone|Buyers?|Reps?|Candidates?)\b[^.]{0,80}?\bshould\b", re.I)

    def test_hartmann_summary(self):
        lede = all_suppliers()["Paul Hartmann (HARTMANN)"]["deepDive"]["lede"]
        self.assertNotIn("should", lede)
        self.assertIn("shift away from lower-margin NHS tender business toward private pay "
                      "and formulary-listed wound care.", lede)

    def test_no_summary_gives_the_reader_advice(self):
        for f in ("data/supplier-seed.json", "data/supplier-index.json"):
            bad = []
            for s in load(f)["suppliers"]:
                lede = (s.get("deepDive") or {}).get("lede") or ""
                m = self.ADVICE.search(lede)
                if m:
                    bad.append((s["name"], m.group(0)))
            self.assertEqual(bad, [], f)


class CompanyReportHeaderLinksAreDistinct(unittest.TestCase):
    """HARTMANN's header showed two "Website" pills (hartmann.co.uk redirects
    to www.hartmann.info/en-GB). No header may show two pills that read the same."""

    @classmethod
    def setUpClass(cls):
        cls.sup = all_suppliers()
        cls.names = sorted(cls.sup)
        cls.out = dict(zip(cls.names, node_map(
            "/* header-links:start", "/* header-links:end */", "headerLinks",
            [[(cls.sup[n].get("deepDive") or {}).get("links") or [], cls.sup[n].get("links") or []]
             for n in cls.names])))

    def test_hartmann_has_one_website_pill(self):
        labels = [l["label"] for l in self.out["Paul Hartmann (HARTMANN)"]]
        self.assertEqual(labels.count("Website"), 1, labels)
        self.assertEqual([l for l in labels if l.startswith("Website")], ["Website"])

    def test_no_company_has_two_pills_with_one_label(self):
        dup = {n: [l["label"] for l in ls] for n, ls in self.out.items()
               if len({l["label"].lower() for l in ls}) != len(ls)}
        self.assertEqual(dup, {})

    def test_same_site_twice_is_one_pill(self):
        (a, b) = node_map("/* header-links:start", "/* header-links:end */", "headerLinks",
                          [[[{"label": "Website", "url": "https://example.com/"}],
                            [{"label": "Website", "url": "https://www.example.com"}]],
                           [[{"label": "Website", "url": "https://a.example.com/uk"}],
                            [{"label": "Website", "url": "https://b.example.org"}]]])
        self.assertEqual(len(a), 1)
        self.assertEqual([l["label"] for l in b], ["Website", "Website (b.example.org)"])


class CompanyReportNamesNoInternalFiles(unittest.TestCase):
    """Method and source text a member reads names the source, never a repo
    file, script or curator. The award method text named data/tender-history.json."""

    def test_award_method_text(self):
        aw = load("data/company-awards.json")
        for k in ("source", "sectionRule", "matchRule"):
            self.assertIsNone(INTERNAL.search(aw.get(k) or ""), k)
        self.assertIsNone(INTERNAL.search((aw.get("coverage") or {}).get("note") or ""))
        self.assertIn("the Hub's tender and award history", aw["source"])

    def test_award_generator_does_not_write_the_file_name(self):
        src = read("scripts/refresh_awards.py")
        self.assertNotIn('"same two feeds held in data/tender-history.json"', src)
        self.assertNotIn('"Awards are indexed from (1) the award history in %s', src)

    def test_rendered_deep_dive_and_background_prose(self):
        bad = []
        for n, s in all_suppliers().items():
            d = s.get("deepDive") or {}
            texts = [d.get(k) for k in ("lede", "sources", "peopleNote", "interview", "tagline")]
            texts += list(d.get("marketPosition") or []) + list(d.get("ownership") or [])
            texts += [st.get("n") for st in d.get("stats") or [] if isinstance(st, dict)]
            texts += [b.get("text") for b in s.get("background") or [] if isinstance(b, dict)]
            for t in texts:
                if isinstance(t, str) and INTERNAL.search(t):
                    bad.append((n, INTERNAL.search(t).group(0)))
        self.assertEqual(bad, [])

    def test_register_pending_and_range_text(self):
        fin = load("data/company-financials.json")["companies"]
        bad = [n for n, r in fin.items() if INTERNAL.search(str(r.get("matchedOn") or ""))]
        self.assertEqual(bad, [])
        self.assertIsNone(INTERNAL.search(load("data/pending-awards.json").get("rule") or ""))
        sp = load("data/supplier-products.json")["suppliers"]
        bad = [(n, k) for n, r in sp.items() for k in ("filingRule", "notSold")
               if INTERNAL.search(str(r.get(k) or ""))]
        self.assertEqual(bad, [])


# ---------------------------------------------------------------------------
# HARTMANN tool gaps left by the wound reconciliation (msh-compare-data 9a16a7c,
# report hartmann-product-reconciliation-2026-09-30.md), closed 30/09/2026.
# ---------------------------------------------------------------------------

def js_regex(src, anchor):
    """The JS regex literal that follows `anchor` in src, as a Python pattern."""
    rest = src.split(anchor, 1)[1]
    body = rest[rest.index("/") + 1:]
    out, i = [], 0
    while body[i] != "/":
        if body[i] == "\\":
            out.append(body[i:i + 2]); i += 2; continue
        out.append(body[i]); i += 1
    return re.compile("".join(out))


class ComparisonWoundCareTypes(unittest.TestCase):
    """ES Gauze (typed "swab") and Omnistrip ("skin closure") vanished once
    Wound care was picked, because neither type was on the Wound care list.
    Adding "swab" must not pull skin-prep or theatre swabs into Wound care."""

    def setUp(self):
        self.src = read("app/comparison.js")
        line = [l for l in self.src.splitlines() if l.strip().startswith("'wound care': [")][0]
        self.wound = re.findall(r"'([^']+)'", line.split(":", 1)[1])
        self.rx = js_regex(self.src, "'wound care': { 'swab':")

    def test_swab_and_closure_types_are_wound_care(self):
        for t in ("swab", "skin closure", "wound closure", "dressing", "bandage", "tape"):
            self.assertIn(t, self.wound)

    def test_exclusion_is_applied_in_both_filters(self):
        self.assertEqual(self.src.count("if (spec && specExcludes(spec.toLowerCase(), p))"), 2)

    def test_skin_prep_and_theatre_swabs_stay_out(self):
        for name in ("AEROWIPE 70% Isopropyl Alcohol Swab 3 x 3cm Box/100",
                     "AEROWIPE 10% Povidone Iodine Swabs 60 x 33mm Box/100",
                     "Preinjection Swabs Pack 100",
                     "Abdominal Swabs Gauze", "Surgical Swabs Standard Nonwoven"):
            self.assertTrue(self.rx.search(name.lower()), name)

    def test_wound_swabs_stay_in(self):
        for name in ("ES Gauze (gauze swabs)", "Blue Dot Sterile Gauze Swabs 5Cm X 5Cm Pack 5",
                     "Cutimed Sorbact Swab", "Gauze Swab",
                     "AEROSWAB Sterile White Non-Woven Swab 10 x 10cm (Packs of 3) Box/25"):
            self.assertFalse(self.rx.search(name.lower()), name)


class ComparisonRivalByCategory(unittest.TestCase):
    """HydroClean Advance (Differentiator category wound:deb, Debridement &
    irrigation) was offered honey, silver and contact-layer dressings as its
    closest rivals, matched on generic words. The held category now drives the
    suggestion first; the word match follows it as the fallback."""

    def setUp(self):
        self.src = read("app/comparison.js")

    def test_category_lookup_is_loaded_and_fails_soft(self):
        self.assertIn("var PCATURL = BASE + 'data/product-categories.json' + CB;", self.src)
        self.assertIn("fetch(PCATURL).then(function(r){return r.json();}).catch(function(){return {categories:{}};})", self.src)

    def test_same_category_first_then_word_match(self):
        body = self.src.split("function competitorsOf(mine, supFilter){", 1)[1].split("return out.slice(0, 12);", 1)[0]
        self.assertIn("var myCat = catOf(mine);", body)
        self.assertIn("catOf(p) === myCat", body)
        self.assertLess(body.index("var myCat = catOf(mine);"), body.index("if (mine.type){"))
        self.assertIn("var mt = sigTokens(mine.name);", body)

    def test_only_this_suppliers_lines_count(self):
        self.assertIn("if (!it || (s && !lineIsSuppliers(it, s))) return;", self.src)

    def test_lookup_is_derived_and_rebuilt_with_the_differentiator(self):
        wf = read(".github/workflows/differentiator.yml")
        self.assertIn("python3 scripts/build_product_categories.py", wf)
        self.assertIn("git add data/differentiator.json data/product-categories.json", wf)
        self.assertLess(wf.index("scripts/build_differentiator.py"), wf.index("scripts/build_product_categories.py"))

    def test_hydroclean_lines_are_held_as_debridement(self):
        cats = json.loads(read("data/product-categories.json"))["categories"]
        deb = set(cats["wound:deb"]["npc"])
        cache = json.loads(read("data/nhssc-cache.json"))["products"]
        entry = [v for k, v in cache.items() if k.lower().startswith("hydroclean advance")][0]
        npcs = {it["npc"] for it in entry["items"] if "HARTMANN" in (it.get("supplier") or "").upper()}
        self.assertTrue(npcs)
        self.assertTrue(npcs & deb, "no HydroClean Advance line is filed wound:deb")


SPLIT_SCRIPT = r"""
const fs = require('fs');
const A = process.argv.slice(-4);
const src = fs.readFileSync(A[0], 'utf8');
const blk = src.split('    /* brand-lines:start')[1].split('/* brand-lines:end */')[0];
const F = new Function('/*' + blk + '; return { splitSeedProduct: splitSeedProduct, ownFirstWords: ownFirstWords };')();
const idx = JSON.parse(fs.readFileSync(A[1], 'utf8'));
const seed = JSON.parse(fs.readFileSync(A[2], 'utf8'));
const cache = JSON.parse(fs.readFileSync(A[3], 'utf8')).products;
const nk = x => String(x || '').toLowerCase().replace(/\s+/g, ' ').trim();
const C = {}; for (const k in cache) C[nk(k)] = cache[k];
const s = idx.suppliers.filter(x => x.name === 'Paul Hartmann (HARTMANN)')[0];
const sd = seed.suppliers.filter(x => x.name === s.name)[0];
if (sd && sd.products && sd.products.length) s.products = sd.products;
const of = F.ownFirstWords(s), out = [], seen = {};
(s.products || []).forEach(p => {
  const n = typeof p === 'string' ? p : p.name;
  const parts = F.splitSeedProduct(n, C[nk(n)], s, of);
  (parts ? parts.map(g => g.name) : [n]).forEach(x => { if (!seen[nk(x)]) { seen[nk(x)] = 1; out.push(x); } });
});
process.stdout.write(JSON.stringify(out));
"""


class HelpMePrepareSplitsLikeComparison(unittest.TestCase):
    """Help me prepare listed HARTMANN's seed search terms verbatim ("Cosmopor
    range (adhesive and film dressings)", "Atrauman range (...)") while Product
    Comparison listed the catalogue brand lines. Both now run one splitting
    block, carried byte for byte in both files."""

    @classmethod
    def setUpClass(cls):
        cls.cmp = read("app/comparison.js")
        cls.mp = read("app/meeting-prep.js")
        cls.node = shutil.which("node")
        cls.names = None
        if cls.node:
            r = subprocess.run(
                [cls.node, "-e", SPLIT_SCRIPT, os.path.join(HERE, "app", "meeting-prep.js"),
                 os.path.join(HERE, "data", "supplier-index.json"),
                 os.path.join(HERE, "data", "supplier-seed.json"),
                 os.path.join(HERE, "data", "nhssc-cache.json")],
                capture_output=True, text=True, timeout=180)
            if r.returncode != 0:
                raise RuntimeError("node split run failed: " + r.stderr)
            cls.names = json.loads(r.stdout)

    @staticmethod
    def block(src):
        return src.split("/* brand-lines:start", 1)[1].split("/* brand-lines:end */", 1)[0]

    def test_one_block_in_both_files(self):
        self.assertEqual(self.block(self.cmp), self.block(self.mp))
        self.assertIn("function splitSeedProduct(name, entry, s, ownFirst){", self.block(self.mp))

    def test_both_tools_call_it(self):
        self.assertIn("var parts = splitSeedProduct(name, entry, s, ownFirst);", self.cmp)
        self.assertIn("var parts = splitSeedProduct(p.n, CACHE[nk(p.n)], co, ownFirst);", self.mp)
        self.assertIn("return (verified || !co) ? norm : splitSeed(co, norm);", self.mp)
        self.assertIn("var NHSSC = BASE + 'data/nhssc-cache.json' + CB;", self.mp)

    def test_hartmann_lists_brand_lines_not_grouped_terms(self):
        if not self.node:
            self.skipTest("node not installed; split not exercised")
        for n in ("Cosmopor E", "Cosmopor IV", "Atrauman Silicone", "Atrauman AG",
                  "RespoSorb Silicone Border", "HydroTac-Comfort", "ES Gauze (gauze swabs)",
                  "Omnistrip (sterile skin closure strips)"):
            self.assertIn(n, self.names)
        for n in ("Cosmopor range (adhesive and film dressings)", "Atrauman range (wound contact layers)",
                  "HydroTac (hydropolymer foam dressing)"):
            self.assertNotIn(n, self.names)
        self.assertFalse([n for n in self.names if ";" in n])
        low = [n.lower() for n in self.names]
        self.assertEqual(len(low), len(set(low)))


class InterviewPrepHartmannLabels(unittest.TestCase):
    """Interview Prep (page 2672 reads data/interview-prep.json) still carried
    HARTMANN's old grouped labels and the old PermaFoam routing sentence."""

    def test_hartmann_record_rebuilt(self):
        doc = json.loads(read("data/interview-prep.json"))
        rec = [r for r in doc["co"] if r["n"] == "Paul Hartmann (HARTMANN)"][0]
        pr = rec.get("pr") or []
        self.assertIn("PermaFoam Classic (non-adhesive foam dressing)", pr)
        self.assertFalse([p for p in pr if ";" in p or "Drug Tariff" in p or "Tracheostomy" in p])


# ---------------------------------------------------------------------------
# MoliCare and HARTMANN's other non-wound products typed (30/09/2026). Since
# 75ac80e split MoliCare into 25 untyped catalogue lines, untyped products
# passed the Wound care type filter and HARTMANN's continence range showed
# under Wound care. Bed Mat 5D was typed "bed" and offered hospital beds.
# ---------------------------------------------------------------------------

SPEC_SCRIPT = r"""
const fs = require('fs'), path = require('path');
const root = process.argv[process.argv.length - 1];
let src = fs.readFileSync(path.join(root, 'app/comparison.js'), 'utf8');
const marker = '    function refreshList(){';
if (src.indexOf(marker) === -1) { process.stderr.write('refreshList() marker gone'); process.exit(3); }
const gw = src.split('\n').filter(l => l.trim().indexOf('var GENERIC_WORDS = ') === 0)[0].trim();
src = src.replace(marker, gw + "\nglobalThis.__X = {P: PRODUCTS, inSpec: inSpec, SPECMAP: SPECMAP, specExcludes: specExcludes, comp: competitorsOf}; throw 'STOP';\n" + marker);
const anyEl = () => new Proxy(function(){}, {get: (t, k) => k === 'style' ? {} : (k === 'value' ? '' : anyEl()), set: () => true, apply: () => anyEl()});
globalThis.document = {getElementById: () => ({innerHTML: '', appendChild(){}}), createElement: () => anyEl()};
globalThis.fetch = (u) => { const rel = u.split('/main/')[1].split('?')[0];
  return Promise.resolve({json: () => Promise.resolve(JSON.parse(fs.readFileSync(path.join(root, rel), 'utf8')))}); };
eval(src);
let waited = 0;
(function poll(){
  if (!globalThis.__X) { if ((waited += 100) > 60000) { process.stderr.write('PRODUCTS never built'); process.exit(4); } return setTimeout(poll, 100); }
  const X = globalThis.__X, H = 'Paul Hartmann (HARTMANN)';
  // subset() as the form runs it with a speciality and company picked, no type
  function shown(spec){
    const allowed = X.SPECMAP[spec.toLowerCase()] || null;
    return X.P.filter(p => p.supplier === H && X.inSpec(p, spec)
      && !(allowed && p.type && allowed.indexOf(p.type) === -1)
      && !X.specExcludes(spec.toLowerCase(), p)).map(p => [p.name, p.type]);
  }
  const mine = X.P.filter(p => p.supplier === H);
  const bm = mine.filter(p => p.name === 'MoliCare Premium Bed Mat 5D')[0];
  process.stdout.write(JSON.stringify({
    types: mine.map(p => [p.name, p.type]),
    wound: shown('Wound care'),
    continence: shown('Continence & urology'),
    bedMatRivals: bm ? X.comp(bm).map(p => [p.name, p.type, p.supplier]) : null
  }));
  process.exit(0);
})();
"""


class HartmannNonWoundTyped(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.node = shutil.which("node")
        cls.out = None
        if cls.node:
            r = subprocess.run([cls.node, "-e", SPEC_SCRIPT, HERE], capture_output=True, text=True, timeout=240)
            if r.returncode != 0:
                raise RuntimeError("node speciality run failed: " + r.stderr)
            cls.out = json.loads(r.stdout)

    def setUp(self):
        if not self.node:
            self.skipTest("node not installed; comparison.js not exercised")

    NON_WOUND = re.compile(r"molicare|sicsac|vala|stellisept|sterillium|baktol|dispenser|peha-soft", re.I)

    def test_wound_care_shows_no_continence_or_hygiene(self):
        bad = [n for n, t in self.out["wound"] if self.NON_WOUND.search(n)]
        self.assertEqual(bad, [])

    def test_wound_care_keeps_the_wound_range(self):
        w = self.out["wound"]
        self.assertEqual(sum(1 for n, t in w if t == "dressing"), 27)
        names = [n for n, t in w]
        for n in ("Mullro (tissue gauze and cotton)", "Tamponadebinde (absorbent ribbon gauze)",
                  "ES Gauze (gauze swabs)", "Omnistrip (sterile skin closure strips)", "Varolast Plus (zinc paste bandage)"):
            self.assertIn(n, names)

    def test_every_molicare_line_is_typed_from_its_catalogue_description(self):
        t = dict(self.out["types"])
        molicare = {n: v for n, v in t.items() if n.startswith("MoliCare")}
        self.assertEqual(len(molicare), 25)
        self.assertFalse([n for n, v in molicare.items() if not v])
        self.assertEqual(t["MoliCare Premium Bed Mat 5D"], "underpad")
        self.assertEqual(t["MoliCare Premium Elastic 6D"], "all-in-one pad")
        self.assertEqual(t["MoliCare Premium Slip Extra Plus"], "all-in-one pad")
        self.assertEqual(t["MoliCare Premium Form 5D"], "shaped pad")
        self.assertEqual(t["MoliCare Premium Men Pad 4D"], "shaped pad")
        self.assertEqual(t["MoliCare Rectangular 3D"], "rectangular pad")
        self.assertEqual(t["MoliCare Premium Mobile 6D"], "pull up pants")
        self.assertEqual(t["MoliCare Fixpants"], "fixation pants")
        self.assertEqual(t["HARTMANN hand hygiene dispensers and single-use pumps"], "dispenser")
        self.assertEqual(t["Baktolin (hand wash)"], "hand wash")
        self.assertEqual(t["Baktolan (skin care cream)"], "moisturiser")
        for n in ("SicSac (disposable sick bag)", "Stellisept med (antimicrobial body wash)",
                  "Vala disposable care range (bibs, towels, washing mitts, sheets)"):
            self.assertTrue(t[n], n)

    def test_continence_shows_the_molicare_range(self):
        c = dict(self.out["continence"])
        self.assertEqual(len([n for n in c if n.startswith("MoliCare")]), 25)

    def test_bed_mat_rivals_are_bed_protection_not_beds(self):
        r = self.out["bedMatRivals"]
        self.assertTrue(r)
        self.assertFalse([x for x in r if x[1] in ("bed", "mattress")])
        self.assertGreaterEqual(sum(1 for x in r if x[1] == "underpad"), len(r) - 1)

    def test_type_alias_and_override_come_from_the_data_file(self):
        pt = json.loads(read("data/product-types.json"))
        self.assertEqual(pt["type_alias"]["bed mat"], "underpad")
        self.assertEqual(pt["generic_type_override"]["pump"], "dispenser")
        src = read("app/comparison.js")
        self.assertIn("if (PT && PT.type_alias) TYPE_ALIAS = PT.type_alias;", src)
        # the render-scope `var` copies shadowed the JSON-loaded maps
        body = src.split("function render(index, cfg, seed, nhssc){", 1)[1]
        self.assertNotIn("var GENERIC_TYPE_OVERRIDE", body)
        self.assertNotIn("var CANNULA_DISQUALIFIERS", body)


if __name__ == "__main__":
    unittest.main(verbosity=2)
