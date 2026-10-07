#!/usr/bin/env python3
"""My Hub account state: the PHP snippet and the browser client agree.

hub/wpcode/my-hub-pins.php cleans and merges what a member's browser sends
to /wp-json/msh/v1/my-hub before it is stored; app/hub-account.js applies the
same rules to its own copy (and to the browser fallback). If the two drift,
a star or a "seen" mark looks saved on screen and is gone on the next page.
So every case below runs through BOTH (php and node) and both must give the
expected answer. Stdlib only; php and node are on ubuntu-latest and each is
skipped, loudly, where missing.

    python3 test_my_hub_state.py
"""
import json
import os
import shutil
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
PHP_SNIPPET = os.path.join(HERE, "hub", "wpcode", "my-hub-pins.php")
JS_CLIENT = os.path.join(HERE, "app", "hub-account.js")

# WordPress functions the snippet calls at load time, stubbed so the file can
# be included outside WordPress. Nothing here is called by the pure functions.
PHP_STUBS = r"""
function add_action() {}
"""
PHP_RUN = r"""
$cases = json_decode($argv[1], true);
$out = array();
foreach ($cases as $c) {
  $fn = $c[0]; $args = $c[1];
  if ($fn === 'normState') { $out[] = msh_hub_state_clean($args[0]); }
  elseif ($fn === 'applyBody') { $out[] = msh_hub_state_apply($args[0], $args[1], $args[2]); }
  elseif ($fn === 'starKey') { $out[] = msh_hub_star_key($args[0]); }
  elseif ($fn === 'pins') { $out[] = msh_hub_pins_clean($args[0]); }
}
echo json_encode($out);
"""
NODE_RUN = r"""
const P = require(process.argv[1])._pure;
const cases = JSON.parse(process.argv[2]);
const out = [];
for (const [fn, args] of cases) {
  if (fn === 'normState') out.push(P.normState(args[0]));
  else if (fn === 'applyBody') out.push(P.applyBody(args[0], args[1], args[2]));
  else if (fn === 'starKey') out.push(P.starKey(args[0]));
}
process.stdout.write(JSON.stringify(out));
"""

BLANK = {"v": 1, "wnSeen": [], "tour": False, "tourSeen": False, "briefing": False,
         "phone": False, "scope": "mine", "stars": []}
FW = {"u": "/medical-sales-hub/frameworks/", "t": "Framework Hub", "k": "page", "at": "2026-09-30"}

CASES = [
    # (name, fn, args, expected)
    ("garbage is a blank state", "normState", [None], BLANK),
    ("a list is not a state", "normState", [["x"]], BLANK),
    ("seen ids: valid, unique, strings only",
     "normState", [{"wnSeen": ["a-1", "a-1", "BAD", 7, "b", "x" * 65]}], dict(BLANK, wnSeen=["a-1", "b"])),
    ("seen ids keep the newest 300", "normState",
     [{"wnSeen": ["s%d" % i for i in range(305)]}], dict(BLANK, wnSeen=["s%d" % i for i in range(5, 305)])),
    ("booleans are strict", "normState",
     [{"tour": 1, "tourSeen": "true", "briefing": True, "phone": True}], dict(BLANK, briefing=True, phone=True)),
    ("scope is mine unless all", "normState", [{"scope": "ALL"}], BLANK),
    ("scope all", "normState", [{"scope": "all"}], dict(BLANK, scope="all")),
    ("stars: host stripped, tags stripped, bad dropped, deduped", "normState", [{"stars": [
        {"u": "https://www.medsalesintelligencehub.co.uk/medical-sales-hub/frameworks/", "t": "<b>Framework</b>   Hub", "k": "page", "at": "2026-09-30"},
        {"u": "https://medsalesintelligencehub.co.uk/medical-sales-hub/frameworks/", "t": "Again", "k": "page"},
        {"u": "javascript:alert(1)", "t": "x"},
        {"u": "/medical-sales-hub/a/", "t": "   "},
        {"u": "https://example.org/story", "t": "A story", "k": "story", "at": "1 Oct"},
        ["not", "a", "star"],
    ]}], dict(BLANK, stars=[FW, {"u": "https://example.org/story", "t": "A story", "k": "story", "at": ""}])),
    ("bare host is the root path", "starKey", ["https://medsalesintelligencehub.co.uk"], "/"),
    ("empty stays empty (and is then rejected)", "starKey", [""], ""),
    ("titles cut at 200", "normState", [{"stars": [{"u": "/x/", "t": "y" * 250}]}],
     dict(BLANK, stars=[{"u": "/x/", "t": "y" * 200, "k": "page", "at": ""}])),
    ("state patch sets only the keys it names, never v", "applyBody",
     [dict(BLANK, briefing=True, stars=[FW]), {"state": {"tour": True, "v": 9, "nonsense": 1}}, "2026-10-01"],
     dict(BLANK, briefing=True, tour=True, stars=[FW])),
    ("star goes first, same address replaced, dated today", "applyBody",
     [dict(BLANK, stars=[{"u": "/a/", "t": "A", "k": "page", "at": ""}, FW]),
      {"star": {"u": "https://medsalesintelligencehub.co.uk/medical-sales-hub/frameworks/", "t": "Framework Hub", "k": "page"}},
      "2026-10-01"],
     dict(BLANK, stars=[dict(FW, at="2026-10-01"), {"u": "/a/", "t": "A", "k": "page", "at": ""}])),
    ("unstar by full URL removes the path", "applyBody",
     [dict(BLANK, stars=[FW]), {"unstar": "https://medsalesintelligencehub.co.uk/medical-sales-hub/frameworks/"}, "2026-10-01"],
     BLANK),
    ("a bad star changes nothing", "applyBody", [dict(BLANK, stars=[FW]), {"star": {"u": "ftp://x", "t": "x"}}, "2026-10-01"],
     dict(BLANK, stars=[FW])),
    ("trailing newline is not an id", "normState", [{"wnSeen": ["abc\n", "ok"]}], dict(BLANK, wnSeen=["ok"])),
    ("trailing newline is not a date", "normState",
     [{"stars": [{"u": "/x/", "t": "X", "at": "2026-09-30\n"}]}], dict(BLANK, stars=[{"u": "/x/", "t": "X", "k": "page", "at": ""}])),
    ("title must be a string (true)", "normState", [{"stars": [{"u": "/x/", "t": True}]}], BLANK),
    ("title must be a string (false)", "normState", [{"stars": [{"u": "/x/", "t": False}]}], BLANK),
    ("url must be a string", "normState", [{"stars": [{"u": ["/y/"], "t": "Y"}]}], BLANK),
    ("seen ids must be a list", "normState", [{"wnSeen": {"a": "ok"}}], BLANK),
    ("stars must be a list", "normState", [{"stars": {"a": {"u": "/x/", "t": "X"}}}], BLANK),
    ("title cut counts characters, not UTF-16 units", "normState",
     [{"stars": [{"u": "/x/", "t": "\U0001F600" * 250}]}], dict(BLANK, stars=[{"u": "/x/", "t": "\U0001F600" * 200, "k": "page", "at": ""}])),
    ("protocol-relative path is rejected", "normState",
     [{"stars": [{"u": "https://medsalesintelligencehub.co.uk//evil.com/", "t": "E"}, {"u": "/\\evil.com", "t": "E"}]}], BLANK),
]


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise AssertionError(r.stderr or r.stdout)
    return json.loads(r.stdout)


class StateParity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.php = shutil.which("php")
        cls.node = shutil.which("node")
        calls = [[fn, args] for _, fn, args, _ in CASES]
        cls.php_out = cls.node_out = None
        if cls.php:
            with open(PHP_SNIPPET, encoding="utf-8") as f:
                body = f.read()
            with tempfile.NamedTemporaryFile("w", suffix=".php", delete=False, encoding="utf-8") as t:
                t.write("<?php\n" + PHP_STUBS + "\n" + body + "\n" + PHP_RUN)
                cls.tmp = t.name
            cls.php_out = run([cls.php, cls.tmp, json.dumps(calls)])
        if cls.node:
            cls.node_out = run([cls.node, "-e", NODE_RUN, JS_CLIENT, json.dumps(calls)])

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, "tmp", None):
            os.unlink(cls.tmp)

    def test_php_snippet(self):
        if not self.php:
            self.skipTest("php not installed; the WPCode snippet's rules not exercised")
        for (name, _, _, want), got in zip(CASES, self.php_out):
            self.assertEqual(got, want, "PHP: " + name)

    def test_browser_client(self):
        if not self.node:
            self.skipTest("node not installed; app/hub-account.js not exercised")
        for (name, _, _, want), got in zip(CASES, self.node_out):
            self.assertEqual(got, want, "JS: " + name)

    def test_writes_are_serialised_and_latest_wins(self):
        """Three quick changes: bodies go out one at a time, in order, and a slow
        first reply cannot roll the local copy back."""
        if not self.node:
            self.skipTest("node not installed")
        script = r"""
const A = require(process.argv[1]);
const P = A._pure;
let server = P.blank(), inflight = 0, maxIn = 0; const bodies = [];
globalThis.mshRestNonce = 'n';
globalThis.fetch = (url, o) => {
  if (o.method === 'GET') return Promise.resolve({ ok: true, json: () => Promise.resolve({ saved: true, pins: [], stateSaved: true, state: server }) });
  const body = JSON.parse(o.body); bodies.push(body);
  inflight++; maxIn = Math.max(maxIn, inflight);
  const delay = bodies.length === 1 ? 40 : 1;
  return new Promise(res => setTimeout(() => {
    server = P.applyBody(server, body, '2026-10-01'); inflight--;
    res({ ok: true, json: () => Promise.resolve({ saved: true, pins: [], stateSaved: true, state: server }) });
  }, delay));
};
(async () => {
  await A.load();
  const ps = [A.star({ u: '/a/', t: 'A', k: 'page' }), A.star({ u: '/b/', t: 'B', k: 'page' }), A.saveState({ tour: true })];
  await Promise.all(ps);
  const cur = await A.load();
  process.stdout.write(JSON.stringify({ maxIn, order: bodies.map(b => Object.keys(b)[0] + ':' + (b.star ? b.star.u : '')),
    stars: cur.state.stars.map(s => s.u), tour: cur.state.tour, serverStars: server.stars.map(s => s.u) }));
})();
"""
        out = run([self.node, "-e", script, JS_CLIENT])
        self.assertEqual(out["maxIn"], 1)
        self.assertEqual(out["order"], ["star:/a/", "star:/b/", "state:"])
        self.assertEqual(out["stars"], ["/b/", "/a/"])
        self.assertTrue(out["tour"])
        self.assertEqual(out["serverStars"], ["/b/", "/a/"])

    def test_pins_rule_unchanged(self):
        if not self.php:
            self.skipTest("php not installed")
        got = run([self.php, self.tmp, json.dumps([["pins", [["Live-Desk", "live-desk", "a b", 5, "x" * 81] + ["p%d" % i for i in range(200)]]]])])[0]
        self.assertEqual(got[:2], ["live-desk", "ab"])
        self.assertEqual(len(got), 150)

    def test_snippet_has_no_opening_tag(self):
        with open(PHP_SNIPPET, encoding="utf-8") as f:
            self.assertFalse(f.read().lstrip().startswith("<?php"), "WPCode adds the opening tag itself")


if __name__ == "__main__":
    unittest.main(verbosity=1)
