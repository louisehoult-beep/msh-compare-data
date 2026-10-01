"""scripts/fcm_push.py and push_alerts.send_app — Live Desk app alerts (01/10/2026)."""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts"))

import fcm_push as F
import push_alerts as P

MSG = {"title": "Stroke: 2 new items", "body": "Lead", "tag": "msh-news-20261001-09",
       "items": [{"t": "Item %d" % i, "u": "https://x/%d" % i, "s": "", "sp": "Stroke"} for i in range(2)],
       "more": 0}


class ToFcmTests(unittest.TestCase):
    def test_shape(self):
        m = F.to_fcm("tok", MSG)["message"]
        self.assertEqual(m["token"], "tok")
        self.assertEqual(m["notification"], {"title": MSG["title"], "body": "Lead"})
        self.assertTrue(all(isinstance(v, str) for v in m["data"].values()))
        self.assertEqual(len(json.loads(m["data"]["items"])), 2)

    def test_items_trimmed_to_fit(self):
        big = dict(MSG, items=[{"t": "x" * 140, "u": "https://x/" + "y" * 100, "s": "", "sp": "S"}] * 40)
        m = F.to_fcm("tok", big)["message"]
        self.assertLessEqual(len(json.dumps(m["data"]).encode()), F.DATA_MAX)


class SendAppTests(unittest.TestCase):
    def test_not_configured_is_skipped(self):
        logs = []
        self.assertIsNone(P.send_app(None, {}, env={}, log=logs.append))
        self.assertIn("not configured", logs[0])

    def test_fault_never_raises(self):
        logs = []
        out = P.send_app(None, {}, env={"FCM_SERVICE_ACCOUNT": "{not json"}, log=logs.append)
        self.assertIn("error", out)


if __name__ == "__main__":
    unittest.main()
