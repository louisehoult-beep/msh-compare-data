"""Live Desk store membership bridge (plan step D2, 19/11/2026).

Runs the pure functions of hub/wpcode/livedesk-store-bridge.php with php -r
(no WordPress), and checks the PHP signature matches the Deno side
(supabase/functions/livedesk/hub_bridge.ts) byte for byte. Offline; skipped
where php or deno is missing.
"""
import json
import os
import shutil
import subprocess
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SNIPPET = os.path.join(HERE, "hub", "wpcode", "livedesk-store-bridge.php")
BRIDGE_TS = os.path.join(HERE, "supabase", "functions", "livedesk", "hub_bridge.ts")
SECRET = "k" * 48
NOW = 1795118400  # 19/11/2026 20:00 UTC
UID = "0b6c2f3e-1d2a-4c5b-9e8f-7a6b5c4d3e2f"


def php(code):
    src = "require %s; %s" % (json.dumps(SNIPPET), code)
    out = subprocess.run(["php", "-r", src], capture_output=True, text=True, timeout=30)
    if out.returncode:
        raise AssertionError(out.stderr or out.stdout)
    return json.loads(out.stdout)


def body(**over):
    d = {"v": 1, "action": "grant", "email": "Member@Example.co.uk", "plan_id": 691,
         "expires_at": "2026-12-19T20:00:00.000Z", "app_user": UID, "product": "hub.monthly",
         "store": "APP_STORE", "event_id": "evt-1"}
    d.update(over)
    return json.dumps(d)


@unittest.skipUnless(shutil.which("php"), "php not installed")
class BridgePhp(unittest.TestCase):

    def sig(self, t, b):
        return php("echo json_encode('t=%d,s=' . msh_ldb_b64url(hash_hmac('sha256', '%d.' . %s, %s, true)));"
                   % (t, t, php_str(b), php_str(SECRET)))

    def verify(self, header, b, now=NOW, secret=SECRET):
        return php("echo json_encode(msh_ldb_verify_sig(%s, %s, %s, %d));"
                   % (php_str(secret), php_str(header), php_str(b), now))

    def test_signature_accepts_and_refuses(self):
        b = body()
        h = self.sig(NOW, b)
        self.assertTrue(self.verify(h, b))
        self.assertTrue(self.verify(h, b, now=NOW + 299))
        self.assertFalse(self.verify(h, b, now=NOW + 301), "stale")
        self.assertFalse(self.verify(h, b + " "), "body changed")
        self.assertFalse(self.verify(h, b, secret="x" * 48), "other secret")
        self.assertFalse(self.verify(h, b, secret="short"), "weak secret")
        self.assertFalse(self.verify("", b))

    @unittest.skipUnless(shutil.which("deno"), "deno not installed")
    def test_deno_and_php_sign_the_same(self):
        b = body()
        code = ("import { bridgeHeader } from %s; console.log(JSON.stringify(await bridgeHeader(%s, %s, %d)));"
                % (json.dumps("file://" + BRIDGE_TS), json.dumps(SECRET), json.dumps(b), NOW))
        out = subprocess.run(["deno", "eval", "--ext=ts", code], capture_output=True, text=True, timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr)
        deno_header = json.loads(out.stdout.strip())
        self.assertEqual(deno_header, self.sig(NOW, b))
        self.assertTrue(self.verify(deno_header, b))

    def parse(self, b):
        return php("echo json_encode(msh_ldb_parse(%s));" % php_str(b))

    def test_parse(self):
        r = self.parse(body())
        self.assertEqual((r["action"], r["email"], r["plan_id"]), ("grant", "member@example.co.uk", 691))
        self.assertEqual(self.parse(body(plan_id=954)), "plan", "withdrawn trial")
        self.assertEqual(self.parse(body(plan_id=5167)), "plan", "employer not sold in the app")
        self.assertEqual(self.parse(body(plan_id="691")), "plan")
        self.assertEqual(self.parse(body(email="nope")), "email")
        self.assertEqual(self.parse(body(action="delete")), "action")
        self.assertEqual(self.parse(body(app_user="$RCAnonymousID:x")), "app_user")
        self.assertEqual(self.parse(body(expires_at="soon")), "expires_at")
        self.assertEqual(self.parse(body(v=2)), "json")
        ll = self.parse(json.dumps({"v": 1, "action": "login_link", "wp_user_id": 12, "app_user": UID}))
        self.assertEqual(ll["wp_user_id"], 12)
        self.assertEqual(self.parse(json.dumps({"v": 1, "action": "login_link", "wp_user_id": "12", "app_user": UID})),
                         "wp_user_id")

    def decide(self, action, subs):
        req = {"action": action, "plan_id": 691}
        return php("echo json_encode(msh_ldb_decide(json_decode(%s, true), json_decode(%s), %d));"
                   % (php_str(json.dumps(req)), php_str(json.dumps(subs)), NOW))

    def test_decide(self):
        future, past = "2026-12-30 00:00:00", "2026-10-01 00:00:00"
        app = {"id": 5, "subscription_plan_id": 691, "status": "active", "expiration_date": future, "app": True}
        web = {"id": 6, "subscription_plan_id": 690, "status": "active", "expiration_date": future, "app": False}
        lapsed = {"id": 7, "subscription_plan_id": 692, "status": "expired", "expiration_date": past, "app": False}
        other = {"id": 8, "subscription_plan_id": 1234, "status": "active", "expiration_date": future, "app": False}
        self.assertEqual(self.decide("grant", [])["op"], "insert")
        self.assertEqual(self.decide("grant", [other])["op"], "insert", "non-Hub plans ignored")
        self.assertEqual(self.decide("grant", [app, web])["id"], 5, "extend ours first")
        self.assertEqual(self.decide("grant", [web])["op"], "none", "website member: no second record")
        self.assertEqual(self.decide("grant", [lapsed]), {"op": "update", "id": 7, "why": "reuse lapsed subscription"})
        self.assertEqual(self.decide("revoke", [web])["op"], "none", "never end a website subscription")
        self.assertEqual(self.decide("revoke", [app, web])["id"], 5)
        self.assertEqual(self.decide("revoke", [dict(app, status="expired")])["op"], "none")

    def test_may_link_only_bridge_accounts(self):
        r = php("echo json_encode([msh_ldb_may_link('livedesk-app', false), msh_ldb_may_link('', false),"
                " msh_ldb_may_link('livedesk-app', true)]);")
        self.assertEqual(r, [True, False, False])

    def test_login_name(self):
        r = php("$t = ['jane'=>1,'jane2'=>1]; echo json_encode([msh_ldb_login_name('jane@x.com', function($n) use ($t){return isset($t[$n]);}),"
                " msh_ldb_login_name('a.b@x.com', function($n){return false;})]);")
        self.assertEqual(r, ["jane3", "memberab"])


def php_str(s):
    return "'" + s.replace("\\", "\\\\").replace("'", "\\'") + "'"


if __name__ == "__main__":
    unittest.main()
