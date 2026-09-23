#!/usr/bin/env python3
"""Unit tests for scripts/push_alerts.py — the member phone-alert digest.

Standard library only, so scripts/run_unit_tests.py can run it anywhere. The
pywebpush and cryptography paths are exercised only if those libraries happen
to be installed; the digest logic (what is new, who gets what, what it says,
what gets pruned) is what these tests pin down, because that is where a bug
becomes thirty buzzes on a member's phone.
"""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts"))
import push_alerts as pa  # noqa: E402


def item(link, title="t", source="Vascular News"):
    return {"title": title, "link": link, "source": source, "published": "2026-09-22T09:00:00+00:00"}


def write_news(d, slug, items):
    with open(os.path.join(d, slug + ".json"), "w", encoding="utf-8") as fh:
        json.dump({"speciality": slug, "generatedAt": "2026-09-22T05:20:00Z", "items": items}, fh)


LBL = lambda s: {"stroke": "Stroke", "urology": "Urology", "respiratory": "Respiratory"}.get(s, s)


class DiffTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        write_news(self.tmp, "stroke", [item("https://a/1"), item("https://a/2")])
        write_news(self.tmp, "urology", [item("https://b/1")])

    def test_first_run_seeds_and_sends_nothing(self):
        news = pa.load_news(self.tmp)
        new, state = pa.diff_news(news, None)
        self.assertEqual(new, {})
        self.assertEqual(sorted(state["seen"]), ["stroke", "urology"])
        self.assertEqual(state["seen"]["stroke"], ["https://a/1", "https://a/2"])

    def test_only_unseen_links_are_new(self):
        news = pa.load_news(self.tmp)
        _, state = pa.diff_news(news, None)
        write_news(self.tmp, "stroke", [item("https://a/3", "Fresh"), item("https://a/1")])
        new, state2 = pa.diff_news(pa.load_news(self.tmp), state)
        self.assertEqual([i["link"] for i in new["stroke"]], ["https://a/3"])
        self.assertNotIn("urology", new)
        # a link that dropped out of the feed drops out of the seen-set too
        self.assertEqual(state2["seen"]["stroke"], ["https://a/3", "https://a/1"])

    def test_duplicate_links_within_a_file_count_once(self):
        write_news(self.tmp, "stroke", [item("https://a/9"), item("https://a/9")])
        _, state = pa.diff_news(pa.load_news(self.tmp), {"seen": {"stroke": []}})
        self.assertEqual(state["seen"]["stroke"], ["https://a/9"])

    def test_items_without_a_link_are_ignored(self):
        write_news(self.tmp, "stroke", [{"title": "no link"}, item("https://a/1")])
        self.assertEqual(len(pa.load_news(self.tmp)["stroke"]), 1)

    def test_state_roundtrip(self):
        p = os.path.join(self.tmp, "state", "push-alerts.json")
        _, state = pa.diff_news(pa.load_news(self.tmp), None)
        pa.save_state(state, p)
        self.assertEqual(pa.load_state(p)["seen"], state["seen"])
        self.assertIsNone(pa.load_state(os.path.join(self.tmp, "missing.json")))


class MessageTests(unittest.TestCase):
    NEW = {
        "stroke": [item("https://a/3", "Thrombectomy trial reports", "Neuro News"), item("https://a/4", "Second")],
        "urology": [item("https://b/2", "New stent")],
    }

    def test_single_speciality_leads_with_the_headline_and_deep_links(self):
        m = pa.build_message(self.NEW, ["stroke"], labels=LBL)
        self.assertEqual(m["title"], "Stroke: 2 new items")
        self.assertEqual(m["body"], "Thrombectomy trial reports — Neuro News")
        self.assertEqual(m["url"], "https://medsalesintelligencehub.co.uk/medical-sales-hub/stroke/")
        self.assertTrue(m["tag"].startswith("msh-news-"))

    def test_multiple_specialities_summarise_and_link_home(self):
        m = pa.build_message(self.NEW, [], labels=LBL)
        self.assertEqual(m["title"], "Hub news: 3 new items across 2 specialities")
        self.assertEqual(m["body"], "Stroke (2) · Urology (1)")
        self.assertEqual(m["url"], pa.HUB_HOME)

    def test_nothing_for_their_specialities_means_no_message(self):
        self.assertIsNone(pa.build_message(self.NEW, ["respiratory"], labels=LBL))
        self.assertIsNone(pa.build_message({}, [], labels=LBL))

    def test_body_is_clipped(self):
        long = {"stroke": [item("https://a/1", "x" * 400, "S")]}
        m = pa.build_message(long, ["stroke"], labels=LBL)
        self.assertLessEqual(len(m["body"]), pa.BODY_MAX)
        self.assertTrue(m["body"].endswith("…"))

    def test_label_fallback_tidies_the_slug(self):
        self.assertEqual(pa.label_for("vascular-access-and-iv-therapy", panels_dir="/nonexistent"),
                         "Vascular Access and Iv Therapy")


class DeliverTests(unittest.TestCase):
    NEW = {"stroke": [item("https://a/3", "Fresh")], "urology": [item("https://b/2", "Stent")]}

    def rows(self):
        return [
            {"id": 1, "endpoint": "https://push.example/1", "p256dh": "k", "auth": "a", "specialities": ["stroke"]},
            {"id": 2, "endpoint": "https://push.example/2", "p256dh": "k", "auth": "a", "specialities": []},
            {"id": 3, "endpoint": "https://push.example/3", "p256dh": "k", "auth": "a", "specialities": ["respiratory"]},
            {"id": 4, "endpoint": "https://push.example/4", "p256dh": "k", "auth": "a", "specialities": "stroke,urology"},
        ]

    def test_one_message_per_subscriber_filtered_to_their_choice(self):
        sent = []
        def send(row, msg):
            sent.append((row["id"], msg["title"]))
            return True, False, "sent"
        counts = pa.deliver(self.rows(), self.NEW, send, log=lambda *_: None)
        self.assertEqual(counts, {"subscribers": 4, "sent": 3, "skipped": 1, "failed": 0, "pruned": 0})
        titles = dict(sent)
        self.assertEqual(titles[1], "Stroke: 1 new item")
        self.assertIn("2 new items across 2 specialities", titles[2])
        self.assertNotIn(3, titles)                      # nothing new in respiratory
        self.assertIn("2 new items across 2 specialities", titles[4])   # comma string tolerated

    def test_gone_endpoints_are_pruned_and_failures_are_kept(self):
        gone, fails = [], []
        def send(row, msg):
            if row["id"] == 1:
                return False, True, "HTTP 410"
            if row["id"] == 2:
                return False, False, "HTTP 500"
            return True, False, "sent"
        counts = pa.deliver(self.rows(), self.NEW, send, on_gone=lambda r: gone.append(r["id"]),
                            log=lambda m: fails.append(m))
        self.assertEqual(gone, [1])
        self.assertEqual(counts["pruned"], 1)
        self.assertEqual(counts["failed"], 1)
        self.assertEqual(counts["sent"], 1)
        self.assertTrue(any("FAILED" in m for m in fails))


class StoreTests(unittest.TestCase):
    def test_requests_carry_the_service_key_and_prune_by_id(self):
        calls = []
        class Resp:
            def __init__(self, body): self.body = body
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def read(self): return self.body
        def opener(req, data, timeout):
            calls.append((req.get_method(), req.full_url, req.headers, data))
            if req.get_method() == "GET":
                return Resp(json.dumps([
                    {"id": 1, "endpoint": "e", "p256dh": "p", "auth": "a", "specialities": []},
                    {"id": 2, "endpoint": "e2", "p256dh": None, "auth": "a"},   # unusable row
                ]).encode())
            return Resp(b"")
        st = pa.Store("https://x.supabase.co/", "SERVICE", opener=opener)
        rows = st.subscriptions()
        self.assertEqual([r["id"] for r in rows], [1])
        st.delete(1)
        self.assertEqual(calls[0][0], "GET")
        self.assertTrue(calls[0][1].startswith("https://x.supabase.co/rest/v1/push_subscriptions?select="))
        self.assertEqual(calls[0][2]["Apikey"], "SERVICE")
        self.assertEqual(calls[1][0], "DELETE")
        self.assertTrue(calls[1][1].endswith("?id=eq.1"))


class ConfigTests(unittest.TestCase):
    def test_config_carries_only_public_values(self):
        news = {"stroke": [], "urology": []}
        env = {"SUPABASE_URL": "https://x.supabase.co/", "SUPABASE_ANON_KEY": "anon",
               "SUPABASE_SERVICE_KEY": "SECRET"}
        cfg = pa.build_config({"vapidPublicKey": "kept"}, news, env, labels=LBL)
        self.assertEqual(cfg["supabaseUrl"], "https://x.supabase.co")
        self.assertEqual(cfg["supabaseAnonKey"], "anon")
        self.assertEqual(cfg["vapidPublicKey"], "kept")      # no private key given: existing kept
        self.assertEqual(cfg["specialities"], [{"slug": "stroke", "label": "Stroke"},
                                               {"slug": "urology", "label": "Urology"}])
        self.assertNotIn("SECRET", json.dumps(cfg))

    def test_public_key_is_derived_when_cryptography_is_available(self):
        try:
            import cryptography  # noqa: F401
            from cryptography.hazmat.primitives.asymmetric import ec  # noqa: F401
        except BaseException:   # a broken system build panics (pyo3), not raises
            self.skipTest("cryptography not importable here")
        priv = pa.b64url(bytes(range(1, 33)))
        pub = pa.public_key_from_private(priv)
        self.assertEqual(len(pa.b64url_decode(pub)), 65)
        self.assertEqual(pa.b64url_decode(pub)[0], 4)
        cfg = pa.build_config(None, {}, {"VAPID_PRIVATE_KEY": priv})
        self.assertEqual(cfg["vapidPublicKey"], pub)


class CliTests(unittest.TestCase):
    def test_first_run_then_nothing_new_then_dry_run(self):
        tmp = tempfile.mkdtemp()
        write_news(tmp, "stroke", [item("https://a/1", "One")])
        state = os.path.join(tmp, "state.json")
        self.assertEqual(pa.main(["send", "--news-dir", tmp, "--state", state]), 0)
        self.assertEqual(pa.load_state(state)["seen"]["stroke"], ["https://a/1"])
        self.assertEqual(pa.main(["send", "--news-dir", tmp, "--state", state]), 0)
        write_news(tmp, "stroke", [item("https://a/2", "Two"), item("https://a/1", "One")])
        self.assertEqual(pa.main(["send", "--news-dir", tmp, "--state", state, "--dry-run"]), 0)
        # dry run leaves the item new
        self.assertEqual(pa.load_state(state)["seen"]["stroke"], ["https://a/1"])

    def test_unconfigured_send_still_advances_the_seen_set(self):
        # No secrets means no subscribers yet, so nothing is lost by marking
        # today's items seen — and the first configured run then starts clean
        # instead of sending weeks of backlog.
        tmp = tempfile.mkdtemp()
        write_news(tmp, "stroke", [item("https://a/1", "One")])
        state = os.path.join(tmp, "state.json")
        pa.main(["send", "--news-dir", tmp, "--state", state])
        write_news(tmp, "stroke", [item("https://a/2", "Two"), item("https://a/1", "One")])
        for k in ("SUPABASE_URL", "SUPABASE_SERVICE_KEY", "VAPID_PRIVATE_KEY"):
            os.environ.pop(k, None)
        self.assertEqual(pa.main(["send", "--news-dir", tmp, "--state", state]), 0)
        self.assertEqual(pa.load_state(state)["seen"]["stroke"], ["https://a/2", "https://a/1"])
        self.assertEqual(pa.load_state(state)["lastSent"]["reason"], "not configured")

    def test_build_config_writes_and_is_idempotent(self):
        tmp = tempfile.mkdtemp()
        write_news(tmp, "stroke", [])
        cfg = os.path.join(tmp, "alerts", "config.json")
        for k in ("SUPABASE_URL", "SUPABASE_ANON_KEY", "VAPID_PRIVATE_KEY"):
            os.environ.pop(k, None)
        self.assertEqual(pa.main(["build-config", "--news-dir", tmp, "--config", cfg]), 0)
        first = json.load(open(cfg))
        self.assertEqual(first["specialities"][0]["slug"], "stroke")
        self.assertEqual(pa.main(["build-config", "--news-dir", tmp, "--config", cfg]), 0)
        self.assertEqual(json.load(open(cfg))["generatedAt"], first["generatedAt"])


if __name__ == "__main__":
    unittest.main(verbosity=1)
