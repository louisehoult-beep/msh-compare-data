#!/usr/bin/env python3
"""The Live Desk to My Hub landing rule (hub/wpcode/my-hub-landing.php).

Lou, 01/10/2026, option A: a logged-in Hub member who opens /medical-sales-hub/
from outside the Hub (bookmark, email, new tab) goes to My Hub, at most once a
day; a Live Desk link clicked inside the Hub still opens the Live Desk;
?desk=1 always does. Every row below runs through the snippet's own
msh_myhub_landing_decide() under php. Stdlib only; php is on ubuntu-latest and
the test is skipped, loudly, where it is missing.

    python3 test_my_hub_landing.py
"""
import json
import os
import shutil
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SNIPPET = os.path.join(HERE, "hub", "wpcode", "my-hub-landing.php")
STUBS = "function add_action() {}\n"
RUN = r"""
$cases = json_decode($argv[1], true);
$out = array();
foreach ($cases as $c) {
  if (isset($c['member_calls'])) {
    $calls = 0;
    $c['member'] = function () use (&$calls) { $calls++; return true; };
    $d = msh_myhub_landing_decide($c);
    $out[] = array($d[0], $d[1], $calls);
  } else {
    $out[] = msh_myhub_landing_decide($c);
  }
}
echo json_encode($out);
"""

GO = {"is_live_desk": True, "method": "GET", "skip_context": False, "prefetch": False,
      "logged_in": True, "escape": False, "referer": "", "cookie_day": "",
      "today": "2026-10-01", "member": True,
      "hub_hosts": ["medsalesintelligencehub.co.uk", "www.medsalesintelligencehub.co.uk"]}

TABLE = [
    ("bookmark, member, first time today", {}, [True, "send-to-my-hub"]),
    ("email link from Outlook web", {"referer": "https://outlook.office.com/mail/"}, [True, "send-to-my-hub"]),
    ("login bridge from the training site", {"referer": "https://elevateandthrive.uk/login/"}, [True, "send-to-my-hub"]),
    ("Live Desk link inside the Hub", {"referer": "https://medsalesintelligencehub.co.uk/medical-sales-hub/my-hub/"}, [False, "came-from-hub"]),
    ("inside the Hub on www", {"referer": "https://WWW.medsalesintelligencehub.co.uk/x/"}, [False, "came-from-hub"]),
    ("a look-alike host is not the Hub", {"referer": "https://medsalesintelligencehub.co.uk.evil.example/"}, [True, "send-to-my-hub"]),
    ("just logged in on the Hub login page", {"referer": "https://medsalesintelligencehub.co.uk/login/"}, [True, "send-to-my-hub"]),
    ("already sent today", {"cookie_day": "2026-10-01"}, [False, "already-today"]),
    ("sent yesterday, so again today", {"cookie_day": "2026-09-30"}, [True, "send-to-my-hub"]),
    ("escape hatch ?desk=1", {"escape": True}, [False, "escape-param"]),
    ("logged out", {"logged_in": False}, [False, "logged-out"]),
    ("logged in, no Hub plan", {"member": False}, [False, "not-member"]),
    ("another page", {"is_live_desk": False}, [False, "not-live-desk"]),
    ("a POST is never redirected", {"method": "POST"}, [False, "not-get"]),
    ("HEAD is never redirected", {"method": "HEAD"}, [False, "not-get"]),
    ("REST, AJAX, cron, feed, admin", {"skip_context": True}, [False, "admin-ajax-rest-cron-feed"]),
    ("browser prefetch", {"prefetch": True}, [False, "prefetch"]),
    ("an empty today never matches an empty cookie", {"today": ""}, [True, "send-to-my-hub"]),
]


class LandingRule(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.php = shutil.which("php")
        if not cls.php:
            return
        with open(SNIPPET, encoding="utf-8") as f:
            body = f.read()
        with tempfile.NamedTemporaryFile("w", suffix=".php", delete=False, encoding="utf-8") as t:
            t.write("<?php\n" + STUBS + body + "\n" + RUN)
            cls.tmp = t.name

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, "tmp", None):
            os.unlink(cls.tmp)

    def decide(self, rows):
        if not self.php:
            self.skipTest("php not installed; the landing rule not exercised")
        r = subprocess.run([self.php, self.tmp, json.dumps(rows)], capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr or r.stdout)
        return json.loads(r.stdout)

    def test_decision_table(self):
        got = self.decide([dict(GO, **over) for _, over, _ in TABLE])
        for (name, _, want), g in zip(TABLE, got):
            self.assertEqual(g, want, name)

    def test_membership_is_checked_last_and_only_when_needed(self):
        got = self.decide([dict(GO, member_calls=1), dict(GO, member_calls=1, cookie_day="2026-10-01"),
                           dict(GO, member_calls=1, logged_in=False)])
        self.assertEqual(got, [[True, "send-to-my-hub", 1], [False, "already-today", 0], [False, "logged-out", 0]])

    def test_snippet_stays_a_302_with_nocache(self):
        with open(SNIPPET, encoding="utf-8") as f:
            src = f.read()
        self.assertIn("wp_safe_redirect( home_url( '/medical-sales-hub/my-hub/' ), 302 )", src)
        self.assertIn("nocache_headers();", src)
        self.assertIn("is_page( 675 )", src)
        self.assertNotIn("301", src.replace("Never \"tidy\" it to a 301", ""))
        self.assertFalse(src.lstrip().startswith("<?php"), "WPCode adds the opening tag itself")


if __name__ == "__main__":
    unittest.main(verbosity=1)
