#!/usr/bin/env python3
"""Colleague Day Pass: the WPCode snippet's rules (hub/wpcode/colleague-pass.php).

A paying member's code (HUB-NAME-XXXX) lets a colleague register on plan 690
at £0 until the end of the next day. The rules under test: code format and
alphabet (no 0/O/1/I), who may hold a code (active 690/691/692/694, not an
NHS free-access clinician, not a pass holder), three uses per code per month,
one pass per email ever, no pass for an existing account, a lapsed owner's
code stops, the expiry is end of tomorrow site time, after_create_user
records both sides and sends the two emails, apply_expiry shortens the
subscription and expires it once past, and nothing on the page says "trial".

Runs the real PHP against in-memory WordPress/PMS stubs. Stdlib only; skipped,
loudly, where php is missing.

    python3 test_colleague_pass.py
"""
import json
import os
import shutil
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
PHP_SNIPPET = os.path.join(HERE, "hub", "wpcode", "colleague-pass.php")

PHP_STUBS = r"""
define('DAY_IN_SECONDS', 86400); define('HOUR_IN_SECONDS', 3600);
$GLOBALS['meta'] = array(); $GLOBALS['users'] = array(); $GLOBALS['subs'] = array();
$GLOBALS['opts'] = array(); $GLOBALS['trans'] = array(); $GLOBALS['mail'] = array();
$GLOBALS['errors'] = array(); $GLOBALS['now'] = strtotime('2026-11-02 21:30:00');
$GLOBALS['logged_in'] = 0; $GLOBALS['updates'] = array();
function add_action() {} function add_filter() {} function add_shortcode() {}
function is_admin() { return false; } function wp_doing_ajax() { return false; }
function wp_unslash($v) { return $v; } function user_can($id, $cap) { return !empty($GLOBALS['users'][$id]['admin']); } function absint($v) { return abs((int) $v); } function sanitize_text_field($v) { return trim($v); }
function sanitize_email($v) { return filter_var(trim($v), FILTER_SANITIZE_EMAIL); }
function is_email($v) { return (bool) filter_var($v, FILTER_VALIDATE_EMAIL); }
function wp_rand($a, $b) { return mt_rand($a, $b); }
function remove_accents($s) { return $s; }
function current_time($t) { return $t === 'mysql' ? date('Y-m-d H:i:s', $GLOBALS['now']) : $GLOBALS['now']; }
function wp_date($f, $ts = null) { return date($f, $ts === null ? $GLOBALS['now'] : $ts); }
function get_user_meta($id, $k, $single = true) { return isset($GLOBALS['meta'][$id][$k]) ? $GLOBALS['meta'][$id][$k] : ''; }
function update_user_meta($id, $k, $v) { $GLOBALS['meta'][$id][$k] = $v; return true; }
function get_userdata($id) { return isset($GLOBALS['users'][$id]) ? (object) $GLOBALS['users'][$id] : false; }
function get_users($args) { $out = array(); foreach ($GLOBALS['meta'] as $id => $m) { if (isset($m[$args['meta_key']]) && $m[$args['meta_key']] === $args['meta_value']) { $out[] = $id; } } return $out; }
function email_exists($e) { foreach ($GLOBALS['users'] as $id => $u) { if (strtolower($u['user_email']) === strtolower($e)) { return $id; } } return false; }
function get_option($k, $d = false) { return isset($GLOBALS['opts'][$k]) ? $GLOBALS['opts'][$k] : $d; }
function update_option($k, $v) { $GLOBALS['opts'][$k] = $v; return true; }
function get_transient($k) { return isset($GLOBALS['trans'][$k]) ? $GLOBALS['trans'][$k] : false; }
function set_transient($k, $v) { $GLOBALS['trans'][$k] = $v; return true; }
function wp_mail($to, $s, $b, $h) { $GLOBALS['mail'][] = array('to' => $to, 'subject' => $s, 'body' => $b); return true; }
function wp_login_url() { return 'https://medsalesintelligencehub.co.uk/login/'; }
function admin_url($p) { return 'https://medsalesintelligencehub.co.uk/wp-admin/' . $p; }
function home_url($p = '') { return 'https://medsalesintelligencehub.co.uk' . $p; }
function esc_html($s) { return htmlspecialchars($s); } function esc_attr($s) { return htmlspecialchars($s); } function esc_url($s) { return $s; }
function is_user_logged_in() { return $GLOBALS['logged_in'] > 0; } function get_current_user_id() { return $GLOBALS['logged_in']; }
function do_shortcode($s) { return '<form class="pms-form"><ul></ul></form>'; }
function is_page() { return true; }
class PmsErrors { function add($k, $m) { $GLOBALS['errors'][] = $m; $GLOBALS['errmap'][$k] = $m; } function get_error_message($k) { return isset($GLOBALS['errmap'][$k]) ? $GLOBALS['errmap'][$k] : ''; } }
function pms_errors() { return new PmsErrors(); }
class Sub {
  public $id; public $user_id; public $subscription_plan_id; public $status; public $expiration_date; public $billing_amount;
  function __construct($a) { foreach ($a as $k => $v) { $this->$k = $v; } }
  function update($d) { foreach ($d as $k => $v) { $this->$k = $v; } $GLOBALS['updates'][] = array($this->user_id, $d); $GLOBALS['subs'][$this->id] = $this; return true; }
}
function pms_get_member_subscriptions($args) { $out = array(); foreach ($GLOBALS['subs'] as $s) {
  if ((int) $s->user_id !== (int) $args['user_id']) continue;
  if (isset($args['subscription_plan_id']) && (int) $s->subscription_plan_id !== (int) $args['subscription_plan_id']) continue;
  $out[] = $s; } return $out; }
function user($id, $email, $first, $plan = 0, $status = 'active', $exp = '2027-06-01 00:00:00') {
  $GLOBALS['users'][$id] = array('ID' => $id, 'user_email' => $email, 'first_name' => $first, 'display_name' => $first . ' Test');
  if ($plan) { $GLOBALS['subs'][$id] = new Sub(array('id' => $id, 'user_id' => $id, 'subscription_plan_id' => $plan, 'status' => $status, 'expiration_date' => $exp, 'billing_amount' => 300)); }
}
"""
PHP_RUN = r"""
$cases = json_decode($argv[1], true);
$out = array();
foreach ($cases as $c) {
  $fn = $c[0]; $a = isset($c[1]) ? $c[1] : array();
  if ($fn === 'user') { call_user_func_array('user', $a); $out[] = true; }
  elseif ($fn === 'meta') { update_user_meta($a[0], $a[1], $a[2]); $out[] = true; }
  elseif ($fn === 'now') { $GLOBALS['now'] = strtotime($a[0]); $out[] = true; }
  elseif ($fn === 'login') { $GLOBALS['logged_in'] = $a[0]; $out[] = true; }
  elseif ($fn === 'post') { $_POST = $a[0]; $out[] = true; }
  elseif ($fn === 'code_for') { $out[] = msh_cpass_code_for($a[0]); }
  elseif ($fn === 'valid') { $out[] = msh_cpass_code_valid_format($a[0]); }
  elseif ($fn === 'eligible') { $out[] = msh_cpass_is_eligible_referrer($a[0]); }
  elseif ($fn === 'check') { $out[] = msh_cpass_check($a[0], $a[1]); }
  elseif ($fn === 'expiry') { $out[] = msh_cpass_expiry_from(); }
  elseif ($fn === 'price') { $p = (object) array('id' => $a[0], 'price' => 300, 'sign_up_fee' => 0); $out[] = msh_cpass_filter_plan_price($p, $a[0])->price; }
  elseif ($fn === 'validate') { $GLOBALS['errors'] = array(); msh_cpass_validate_registration(); $out[] = $GLOBALS['errors']; }
  elseif ($fn === 'create') { user($a[0], $a[1], $a[2], 690, 'active', '2027-11-02 00:00:00'); msh_cpass_after_create_user(array('user_id' => $a[0])); $out[] = array('meta' => $GLOBALS['meta'][$a[0]], 'mail' => $GLOBALS['mail'], 'ref_uses' => msh_cpass_uses(get_user_meta($a[0], 'msh_cpass_from')), 'redeemed' => get_option('msh_cpass_redeemed')); $GLOBALS['mail'] = array(); }
  elseif ($fn === 'apply') { $r = msh_cpass_apply_expiry($a[0]); $s = $GLOBALS['subs'][$a[0]]; $out[] = array($r, $s->expiration_date, $s->status, $s->billing_amount); }
  elseif ($fn === 'shortcode') { $out[] = msh_cpass_shortcode(); }
  elseif ($fn === 'uses_month') { $out[] = msh_cpass_uses_this_month($a[0]); }
  elseif ($fn === 'column') { $out[] = msh_cpass_user_column_value('', 'msh_cpass', $a[0]); }
  elseif ($fn === 'billing') { msh_cpass_fill_billing(); $out[] = array_intersect_key($_POST, array_flip(array('pms_billing_first_name','pms_billing_last_name','pms_billing_email','pms_billing_address','pms_billing_city','pms_billing_country'))); }
  elseif ($fn === 'robots') { $out[] = msh_cpass_robots(array('index' => true, 'follow' => true)); }
  elseif ($fn === 'admin') { $GLOBALS['users'][$a[0]]['admin'] = true; $out[] = true; }
  elseif ($fn === 'delete') { msh_cpass_on_delete_user($a[0]); $out[] = array('redeemed' => get_option('msh_cpass_redeemed'), 'uses' => msh_cpass_uses($a[1])); }
}
echo json_encode($out);
"""


@unittest.skipUnless(shutil.which("php"), "php not installed: snippet rules NOT tested")
class PassRules(unittest.TestCase):
    def run_php(self, cases):
        with tempfile.NamedTemporaryFile("w", suffix=".php", delete=False) as t:
            src = open(PHP_SNIPPET).read().replace("<?php", "", 1)
            t.write("<?php\n" + PHP_STUBS + src + PHP_RUN)
        try:
            r = subprocess.run(["php", t.name, json.dumps(cases)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            return json.loads(r.stdout)
        finally:
            os.unlink(t.name)

    REF = [["user", [10, "sam@acme.com", "Sam", 690]]]

    def test_code_shape_and_alphabet(self):
        out = self.run_php(self.REF + [["code_for", [10]], ["code_for", [10]], ["valid", ["HUB-SAM-AB0D"]], ["valid", ["hub-sam-abcd"]], ["valid", ["HUB-SAM-ABCD"]]])
        code = out[1]
        self.assertRegex(code, r"^HUB-SAM-[ABCDEFGHJKLMNPQRSTUVWXYZ23456789]{4}$")
        self.assertEqual(code, out[2], "a code is never changed once given")
        self.assertFalse(out[3], "0 is not in the alphabet")
        self.assertFalse(out[4], "format check is on the normalised (upper-case) code")
        self.assertTrue(out[5])

    def test_who_may_hold_a_code(self):
        out = self.run_php([
            ["user", [10, "a@x.com", "A", 690]], ["user", [11, "b@x.com", "B", 691]], ["user", [12, "c@x.com", "C", 694]],
            ["user", [13, "d@x.com", "D", 930]], ["user", [14, "e@x.com", "E", 690, "expired"]],
            ["user", [15, "f@x.com", "F", 690]], ["meta", [15, "msh_nhs_email", "f@nhs.net"]],
            ["user", [16, "g@x.com", "G", 690]], ["meta", [16, "msh_cpass_from", 10]],
            ["user", [17, "h@x.com", "H", 0]],
            ["eligible", [10]], ["eligible", [11]], ["eligible", [12]], ["eligible", [13]], ["eligible", [14]], ["eligible", [15]], ["eligible", [16]], ["eligible", [17]],
        ])
        self.assertEqual(out[-8:], [True, True, True, False, False, False, False, False])

    def test_billing_fields_filled_for_a_valid_pass_request_only(self):
        post = {"msh_cpass_choice": "1", "msh_cpass_code": "HUB-SAM-ABCD", "user_email": "new@acme.com", "first_name": "New", "last_name": "Person", "subscription_plans": "690", "pms_billing_city": "Leeds"}
        setup = self.REF + [["meta", [10, "msh_cpass_code", "HUB-SAM-ABCD"]]]
        b = self.run_php(setup + [["post", [post]], ["billing"]])[3]
        self.assertEqual(b, {"pms_billing_first_name": "New", "pms_billing_last_name": "Person", "pms_billing_email": "new@acme.com", "pms_billing_address": "Colleague day pass (no charge, no invoice)", "pms_billing_city": "Leeds", "pms_billing_country": "GB"})
        bad = dict(post, msh_cpass_code="HUB-SAM-ZZZZ")
        self.assertEqual(self.run_php(setup + [["post", [bad]], ["billing"]])[3], {"pms_billing_city": "Leeds"}, "an invalid request is left for PMS to reject as normal")
        self.assertFalse(self.run_php(setup + [["post", [{"user_email": "x@y.com"}]], ["billing"]])[3], "ordinary registrations untouched")

    def test_visitor_sees_the_code_error_above_the_form(self):
        bad = {"msh_cpass_choice": "1", "msh_cpass_code": "HUB-SAM-ZZZZ", "user_email": "new@acme.com", "subscription_plans": "690"}
        out = self.run_php(self.REF + [["post", [bad]], ["validate"], ["shortcode"]])
        self.assertIn('class="msh-cpass-error"', out[3]); self.assertIn("do not recognise", out[3])
        self.assertNotIn("msh-cpass-error", self.run_php(self.REF + [["shortcode"]])[1])

    def test_admin_holds_a_code_without_a_monthly_cap(self):
        uses = [{"month": "2026-11", "on": "2026-11-01", "hash": "x", "user": 1}] * 3
        out = self.run_php([["user", [1, "lou@x.com", "Louise", 0]], ["admin", [1]], ["meta", [1, "msh_cpass_code", "HUB-LOUISE-ABCD"]], ["meta", [1, "msh_cpass_uses", uses]],
                            ["eligible", [1]], ["check", ["HUB-LOUISE-ABCD", "new@acme.com"]], ["login", [1]], ["shortcode"]])
        self.assertTrue(out[4]); self.assertTrue(out[5]["ok"]); self.assertIn("No monthly limit", out[7])

    def test_deleting_a_pass_holder_frees_the_address(self):
        post = {"msh_cpass_choice": "1", "msh_cpass_code": "HUB-SAM-ABCD", "user_email": "new@acme.com", "subscription_plans": "690"}
        out = self.run_php(self.REF + [["meta", [10, "msh_cpass_code", "HUB-SAM-ABCD"]], ["post", [post]], ["validate"], ["create", [30, "new@acme.com", "New"]], ["delete", [30, 10]], ["post", [{}]]])
        self.assertEqual(out[5], {"redeemed": [], "uses": []})

    def test_check_refusals(self):
        code = "HUB-SAM-ABCD"
        cases = [
            ["check", ["", "new@acme.com"]],
            ["check", ["HUB-SAM-0000", "new@acme.com"]],
            ["check", ["HUB-ZED-ABCD", "new@acme.com"]],
            ["check", [code.lower() + " ", "new@acme.com"]],
            ["check", [code, "not-an-email"]],
            ["check", [code, "old@acme.com"]],
        ]
        out = self.run_php(self.REF + [["meta", [10, "msh_cpass_code", code]], ["user", [20, "old@acme.com", "Old", 0]]] + cases)[3:]
        self.assertFalse(out[0]["ok"]); self.assertIn("enter the colleague code", out[0]["message"])
        self.assertFalse(out[1]["ok"]); self.assertIn("right form", out[1]["message"])
        self.assertFalse(out[2]["ok"]); self.assertIn("do not recognise", out[2]["message"])
        self.assertTrue(out[3]["ok"], "case and spaces are forgiven"); self.assertEqual(out[3]["referrer"], 10)
        self.assertFalse(out[4]["ok"]); self.assertIn("email address", out[4]["message"])
        self.assertFalse(out[5]["ok"]); self.assertIn("already a Hub account", out[5]["message"])

    def test_lapsed_owner_code_stops(self):
        out = self.run_php([["user", [10, "sam@acme.com", "Sam", 690, "expired"]], ["meta", [10, "msh_cpass_code", "HUB-SAM-ABCD"]], ["check", ["HUB-SAM-ABCD", "new@acme.com"]]])
        self.assertFalse(out[-1]["ok"]); self.assertIn("no longer active", out[-1]["message"])

    def test_three_a_month_one_per_email(self):
        uses = [{"month": "2026-11", "on": "2026-11-01", "hash": "x", "user": 1}] * 3
        out = self.run_php(self.REF + [["meta", [10, "msh_cpass_code", "HUB-SAM-ABCD"]], ["meta", [10, "msh_cpass_uses", uses]],
                                       ["check", ["HUB-SAM-ABCD", "new@acme.com"]], ["now", ["2026-12-01 09:00:00"]], ["check", ["HUB-SAM-ABCD", "new@acme.com"]]])
        self.assertFalse(out[3]["ok"]); self.assertIn("most times it can this month", out[3]["message"])
        self.assertTrue(out[5]["ok"], "the count resets with the calendar month")
        out = self.run_php(self.REF + [["meta", [10, "msh_cpass_code", "HUB-SAM-ABCD"]], ["post", [{"msh_cpass_choice": "1", "msh_cpass_code": "HUB-SAM-ABCD", "user_email": "new@acme.com", "subscription_plans": "690"}]],
                                       ["create", [30, "new@acme.com", "New"]], ["check", ["HUB-SAM-ABCD", "NEW@acme.com"]]])
        self.assertFalse(out[-1]["ok"]); self.assertIn("already had a colleague day", out[-1]["message"])

    def test_expiry_is_end_of_tomorrow(self):
        out = self.run_php([["expiry"], ["now", ["2026-11-30 23:50:00"]], ["expiry"]])
        self.assertEqual(out[0], "2026-11-03 23:59:59")
        self.assertEqual(out[2], "2026-12-01 23:59:59")

    def test_price_only_for_a_valid_request(self):
        post = {"msh_cpass_choice": "1", "msh_cpass_code": "HUB-SAM-ABCD", "user_email": "new@acme.com", "subscription_plans": "690"}
        setup = self.REF + [["meta", [10, "msh_cpass_code", "HUB-SAM-ABCD"]]]
        self.assertEqual(self.run_php(setup + [["post", [post]], ["price", [690]], ["price", [691]], ["validate"]])[3:], [0, 300, []])
        bad = dict(post, msh_cpass_code="HUB-SAM-ZZZZ")
        out = self.run_php(setup + [["post", [bad]], ["price", [690]], ["validate"]])
        self.assertEqual(out[3], 300); self.assertIn("do not recognise", out[4][0])
        honey = dict(post, msh_cpass_website="http://spam")
        out = self.run_php(setup + [["post", [honey]], ["price", [690]], ["validate"]])
        self.assertEqual(out[3], 300); self.assertIn("Something went wrong", out[4][0])
        self.assertEqual(self.run_php(setup + [["post", [{}]], ["price", [690]], ["validate"]])[3:], [300, []], "ordinary registrations are untouched")

    def test_attempt_limit(self):
        bad = {"msh_cpass_choice": "1", "msh_cpass_code": "HUB-SAM-ZZZZ", "user_email": "new@acme.com", "subscription_plans": "690"}
        out = self.run_php(self.REF + [["post", [bad]]] + [["validate"]] * 6)
        self.assertIn("do not recognise", out[3][0]); self.assertIn("Too many attempts", out[-1][0])

    def test_after_create_user_and_emails(self):
        post = {"msh_cpass_choice": "1", "msh_cpass_code": "HUB-SAM-ABCD", "user_email": "new@acme.com", "subscription_plans": "690"}
        out = self.run_php(self.REF + [["meta", [10, "msh_cpass_code", "HUB-SAM-ABCD"]], ["post", [post]], ["validate"], ["create", [30, "new@acme.com", "New"]], ["uses_month", [10]], ["column", [30]], ["column", [10]]])
        self.assertEqual(out[3], [])
        r = out[4]
        self.assertEqual(r["meta"]["msh_cpass_from"], 10)
        self.assertEqual(r["meta"]["msh_cpass_expires"], "2026-11-03 23:59:59")
        self.assertEqual(len(r["ref_uses"]), 1); self.assertEqual(r["ref_uses"][0]["month"], "2026-11")
        self.assertEqual(len(r["redeemed"]), 1)
        self.assertEqual([m["to"] for m in r["mail"]], ["new@acme.com", "louisehoult@elevateandthrive.uk"])
        self.assertIn("Sam Test has given you a day", r["mail"][0]["body"])
        self.assertIn("Tuesday 3 November at midnight", r["mail"][0]["body"])
        self.assertIn("join-the-hub", r["mail"][0]["body"])
        self.assertIn("1 of 3 this month", r["mail"][1]["body"])
        for m in r["mail"]:
            self.assertNotIn("trial", (m["subject"] + m["body"]).lower())
        self.assertEqual(out[5], 1)
        self.assertIn("Pass from Sam Test, until 2026-11-03 23:59:59", out[6])
        self.assertIn("HUB-SAM-ABCD (1 used)", out[7])
        # no earlier validation call in this request: the hook re-checks allowing the new account's own address
        r = self.run_php(self.REF + [["meta", [10, "msh_cpass_code", "HUB-SAM-ABCD"]], ["post", [post]], ["create", [30, "new@acme.com", "New"]]])[3]
        self.assertEqual(r["meta"]["msh_cpass_from"], 10)

    def test_apply_expiry_shortens_then_expires(self):
        setup = [["user", [30, "new@acme.com", "New", 690]], ["meta", [30, "msh_cpass_from", 10]], ["meta", [30, "msh_cpass_expires", "2026-11-03 23:59:59"]]]
        out = self.run_php(setup + [["apply", [30]], ["apply", [30]], ["now", ["2026-11-04 00:00:01"]], ["apply", [30]]])
        self.assertEqual(out[3], [True, "2026-11-03 23:59:59", "active", 0])
        self.assertEqual(out[4], [True, "2026-11-03 23:59:59", "active", 0], "idempotent")
        self.assertEqual(out[6], [True, "2026-11-03 23:59:59", "expired", 0])
        self.assertEqual(self.run_php([["user", [31, "x@y.com", "X", 690]], ["apply", [31]]])[1][0], False, "not a pass holder: untouched")
        pend = [["user", [32, "p@y.com", "P", 690, "pending"]], ["meta", [32, "msh_cpass_from", 10]], ["meta", [32, "msh_cpass_expires", "2026-11-03 23:59:59"]]]
        self.assertEqual(self.run_php(pend + [["apply", [32]]])[3], [True, "2026-11-03 23:59:59", "active", 0], "manual gateway's pending becomes active within the day")
        self.assertEqual(self.run_php(pend + [["now", ["2026-11-04 00:00:01"]], ["apply", [32]]])[4][2], "pending", "a pending pass that is already past is left for Lou, never activated")

    def test_page_states(self):
        setup = self.REF + [["meta", [10, "msh_cpass_code", "HUB-SAM-ABCD"]],
                            ["user", [30, "new@acme.com", "New", 690]], ["meta", [30, "msh_cpass_from", 10]], ["meta", [30, "msh_cpass_expires", "2026-11-03 23:59:59"]],
                            ["user", [40, "none@acme.com", "None", 0]]]
        out = self.run_php(setup + [["shortcode"], ["login", [10]], ["shortcode"], ["login", [30]], ["shortcode"], ["now", ["2026-11-05 09:00:00"]], ["shortcode"], ["login", [40]], ["shortcode"]])
        visitor, referrer, holder, ended, other = out[6], out[8], out[10], out[12], out[14]
        self.assertIn('class="pms-form"', visitor); self.assertIn("msh-cpass-register", visitor)
        self.assertIn("HUB-SAM-ABCD", referrer); self.assertIn("colleague-pass/?code=HUB-SAM-ABCD", referrer); self.assertIn("Used 0 of 3 this month", referrer)
        self.assertIn("more hour", holder); self.assertIn("Tuesday 3 November", holder); self.assertIn("join-the-hub", holder)
        self.assertIn("has ended", ended); self.assertIn("join-the-hub", ended)
        self.assertIn("Join the Hub", other)
        for html in (visitor, referrer, holder, ended, other):
            self.assertNotIn("trial", html.lower())

    def test_page_is_noindex(self):
        self.assertEqual(self.run_php([["robots"]])[0], {"follow": True, "noindex": True})

    def test_source_never_says_trial_to_members(self):
        src = open(PHP_SNIPPET).read()
        body = src.split("Process:", 1)[1]  # after the header comment
        for line in body.splitlines():
            if "'" in line or '"' in line:
                self.assertNotRegex(line.lower(), r"['\"][^'\"]*trial", line)


if __name__ == "__main__":
    unittest.main(verbosity=1)
