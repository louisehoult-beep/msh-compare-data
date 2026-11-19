#!/usr/bin/env python3
"""Live Desk app in-app mode (hub/wpcode/livedesk-in-app-mode.php), step C of the
Hub-in-the-app plan (19/11/2026). Runs the snippet's own msh_inapp_platform()
and msh_inapp_decide() under php; skipped, loudly, where php is missing.

    python3 test_livedesk_in_app_mode.py
"""
import json
import os
import shutil
import subprocess
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SNIPPET = os.path.join(HERE, "hub", "wpcode", "livedesk-in-app-mode.php")
RUN = r"""
$cases = json_decode($argv[1], true);
$out = array();
foreach ($cases as $c) {
  $out[] = isset($c['ua_only']) ? msh_inapp_platform($c['ua_only']) : msh_inapp_decide($c);
}
echo json_encode($out);
"""
UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MSHLiveDeskApp/ios"
GO = {"ua": UA, "method": "GET", "skip_context": False, "logged_in": True, "page_id": 1174}

DECIDE = [
    ("join page in the app", {}, [True, "hidden-in-app"]),
    ("every hidden page", None, None),
    ("android token", {"ua": "Mozilla/5.0 (Linux; Android 15) Chrome/131 Mobile MSHLiveDeskApp/android"}, [True, "hidden-in-app"]),
    ("ordinary phone browser", {"ua": "Mozilla/5.0 (iPhone) Safari/605"}, [False, "not-app"]),
    ("token glued to another word", {"ua": "Mozilla/5.0 NotMSHLiveDeskApp/ios"}, [False, "not-app"]),
    ("unknown platform", {"ua": "Mozilla/5.0 MSHLiveDeskApp/windows"}, [False, "not-app"]),
    ("a speciality desk stays", {"page_id": 2729}, [False, "not-hidden"]),
    ("My Hub stays", {"page_id": 4404}, [False, "not-hidden"]),
    ("logged out is left to the cached page and the script", {"logged_in": False}, [False, "logged-out"]),
    ("POST is never redirected", {"method": "POST"}, [False, "not-get"]),
    ("REST and admin skipped", {"skip_context": True}, [False, "admin-ajax-rest-cron-feed"]),
]
HIDDEN = [685, 1174, 687, 167, 166, 165, 4802, 4463, 4504]


@unittest.skipUnless(shutil.which("php"), "php is not installed: in-app mode rules NOT TESTED")
class InAppMode(unittest.TestCase):
    def run_php(self, cases):
        code = open(SNIPPET).read()
        src = "<?php\n" + code + "\n" + RUN
        r = subprocess.run(["php", "-r", src.replace("<?php\n", "", 1), json.dumps(cases)],
                           capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr or r.stdout)
        return json.loads(r.stdout)

    def test_decide_table(self):
        rows = [(n, d, w) for n, d, w in DECIDE if d is not None]
        got = self.run_php([{**GO, **d} for _, d, _ in rows])
        for (name, _, want), g in zip(rows, got):
            self.assertEqual(g, want, name)

    def test_every_hidden_page_redirects(self):
        got = self.run_php([{**GO, "page_id": i} for i in HIDDEN])
        self.assertTrue(all(g == [True, "hidden-in-app"] for g in got), got)

    def test_platform(self):
        got = self.run_php([{"ua_only": UA}, {"ua_only": "x MSHLiveDeskApp/android"}, {"ua_only": "Safari"}])
        self.assertEqual(got, ["ios", "android", ""])


if __name__ == "__main__":
    unittest.main()
