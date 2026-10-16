#!/usr/bin/env python3
"""Cluster watch (16/10/2026): parsing, change detection from stored state, the merge
into the ICB watch and the gate. Stdlib only, no network.

  python3 test_cluster_watch.py
"""
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "scripts"))
os.chdir(HERE)
import refresh_cluster_watch as R  # noqa: E402
import refresh_icb_watch as I  # noqa: E402
import verify as v  # noqa: E402

CL = {"id": "c", "name": "C", "icbs": ["QHL", "QUA"]}
DOCLIB = {"id": "m", "label": "Minutes", "kind": "doclib", "url": "https://x.nhs.uk/l", "icb": "QHL",
          "itemPattern": "Minutes", "what": "minutes"}
CHAP = {"id": "ch", "label": "Skin chapter", "kind": "chapter", "url": "https://x.nhs.uk/c", "icb": "QUA",
        "partnerNames": ["Birmingham and Solihull"]}


def cfg(*srcs):
    return {"readOn": "2026-10-16", "clusters": [dict(CL, sources=list(srcs))]}


def run(srcs, prev, reader, day):
    return R.build(cfg(*srcs), prev, reader, day)


def items(*pairs):
    return lambda s: {"items": dict(pairs)}


class Parse(unittest.TestCase):
    def test_doclib_reads_doc_ids_and_filters_titles(self):
        raw = ('<a href="launcher.asp?docID=713">IMOC Minutes 2026 07</a>'
               '<a href="launcher.asp?docID=9">Skin guideline</a><a href="/x">Minutes</a>')
        self.assertEqual(R.parse_items(DOCLIB, raw), {"713": "IMOC Minutes 2026 07"})

    def test_dirlist_reads_file_names(self):
        raw = '<a href="/docs/admin/revisions/a%20Sept.pdf?x=1">a Sept.pdf</a><a href="/home">Home</a>'
        self.assertEqual(R.parse_items({"kind": "dirlist"}, raw), {"a%20Sept.pdf": "a Sept.pdf"})

    def test_linklist_follows_the_pattern(self):
        raw = '<a href="https://h/download_file/1/5">Emollients v2.2.1</a><a href="/other">x</a>'
        got = R.parse_items({"kind": "linklist", "linkPattern": "download_file"}, raw)
        self.assertEqual(list(got.values()), ["Emollients v2.2.1"])

    def test_chapter_text_ignores_session_tokens(self):
        a = R.chapter_text("<p>Emollients UNLID=123 text</p>" + "x" * 600)
        b = R.chapter_text("<p>Emollients UNLID=999 text</p>" + "x" * 600)
        self.assertEqual(a, b)


class Changes(unittest.TestCase):
    def test_first_read_is_a_baseline_with_no_events(self):
        doc = run([DOCLIB], {}, items(("1", "Minutes A")), "2026-10-16")
        self.assertEqual(doc["events"], [])
        self.assertEqual(doc["clusters"][0]["sources"][0]["firstRead"], "2026-10-16")

    def test_new_item_needs_a_second_day(self):
        d1 = run([DOCLIB], {}, items(("1", "Minutes A")), "2026-10-16")
        d2 = run([DOCLIB], d1, items(("1", "Minutes A"), ("2", "Minutes B")), "2026-10-17")
        self.assertEqual(d2["events"], [])
        d2b = run([DOCLIB], d2, items(("1", "Minutes A"), ("2", "Minutes B")), "2026-10-17")
        self.assertEqual(d2b["events"], [])  # same day again: still held
        d3 = run([DOCLIB], d2, items(("1", "Minutes A"), ("2", "Minutes B")), "2026-10-18")
        self.assertEqual(len(d3["events"]), 1)
        e = d3["events"][0]
        self.assertEqual((e["kind"], e["icb"], e["alsoIcbs"]), ("cluster", "QHL", ["QUA"]))
        self.assertIn("Minutes B", e["headline"])
        self.assertTrue(e["sources"][0].startswith("https://"))
        d4 = run([DOCLIB], d3, items(("1", "Minutes A"), ("2", "Minutes B")), "2026-10-19")
        self.assertEqual(len(d4["events"]), 1)  # published once

    def test_item_that_appears_for_one_day_only_is_never_published(self):
        d1 = run([DOCLIB], {}, items(("1", "A")), "2026-10-16")
        d2 = run([DOCLIB], d1, items(("1", "A"), ("2", "B")), "2026-10-17")
        d3 = run([DOCLIB], d2, items(("1", "A")), "2026-10-18")
        self.assertEqual(d3["events"], [])
        self.assertNotIn("item:2", d3["clusters"][0]["sources"][0]["pending"])

    def test_failed_read_keeps_state_and_is_not_a_removal(self):
        d1 = run([DOCLIB], {}, items(("1", "A")), "2026-10-16")

        def boom(s):
            raise OSError("timeout")
        d2 = run([DOCLIB], d1, boom, "2026-10-17")
        s = d2["clusters"][0]["sources"][0]
        self.assertEqual((s["status"], len(s["items"]), d2["events"]), ("error", 1, []))
        self.assertTrue(d2["errorsToday"])

    def test_empty_read_where_items_were_stored_is_an_error(self):
        d1 = run([DOCLIB], {}, items(("1", "A")), "2026-10-16")
        d2 = run([DOCLIB], d1, items(), "2026-10-17")
        self.assertEqual(d2["clusters"][0]["sources"][0]["status"], "error")
        self.assertEqual(len(d2["clusters"][0]["sources"][0]["items"]), 1)

    def test_chapter_change_needs_two_days_and_never_says_merged(self):
        def rd(h, text="Emollients"):
            return lambda s: {"hash": h, "chars": 900, "text": text}
        d1 = run([CHAP], {}, rd("aaa"), "2026-10-16")
        d2 = run([CHAP], d1, rd("bbb"), "2026-10-17")
        self.assertEqual(d2["events"], [])
        d3 = run([CHAP], d2, rd("bbb"), "2026-10-18")
        self.assertEqual(len(d3["events"]), 1)
        text = d3["events"][0]["headline"] + d3["events"][0]["detail"]
        self.assertIn("changed", text)
        self.assertIn("does not say the chapter has been merged", text)

    def test_chapter_flapping_hash_is_not_published(self):
        def rd(h):
            return lambda s: {"hash": h, "chars": 900, "text": "Emollients"}
        d = run([CHAP], {}, rd("aaa"), "2026-10-16")
        for day, h in (("2026-10-17", "bbb"), ("2026-10-18", "ccc"), ("2026-10-19", "ddd")):
            d = run([CHAP], d, rd(h), day)
        self.assertEqual(d["events"], [])

    def test_partner_name_appearing_is_reported_after_two_days(self):
        def rd(text):
            return lambda s: {"hash": "h", "chars": 900, "text": text}
        d1 = run([CHAP], {}, rd("Emollients only"), "2026-10-16")
        self.assertEqual(d1["clusters"][0]["sources"][0]["named"], [])
        d2 = run([CHAP], d1, rd("Emollients, shared with Birmingham and Solihull"), "2026-10-17")
        d3 = run([CHAP], d2, rd("Emollients, shared with Birmingham and Solihull"), "2026-10-18")
        self.assertEqual(len(d3["events"]), 1)
        self.assertIn("names Birmingham and Solihull", d3["events"][0]["headline"])


class Merge(unittest.TestCase):
    def test_cluster_events_merge_by_id_for_live_icbs_only(self):
        doc = {"icbs": [{"code": "QHL"}, {"code": "QUA"}], "events": [
            {"id": "a", "date": "2026-10-01", "kind": "curated"}]}
        ev = R.event("2026-10-18", CL, DOCLIB, "h", "d", ["https://x/"])
        bad = dict(ev, id="zz", icb="XXX")
        I.merge_cluster_events(doc, {"events": [ev, bad]})
        I.merge_cluster_events(doc, {"events": [ev]})
        self.assertEqual([e["id"] for e in doc["events"]], [ev["id"], "a"])

    def test_gate_accepts_a_cluster_event(self):
        self.assertIn("cluster", v.ICB_EVENT_KINDS)


class Config(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(HERE, "config", "cluster-watch-sources.json"), encoding="utf-8") as fh:
            self.cfg = json.load(fh)

    def test_every_source_is_https_and_every_gap_has_a_reason(self):
        for cl in self.cfg["clusters"]:
            for s in cl["sources"]:
                self.assertTrue(s["url"].startswith("https://"), s["id"])
                self.assertIn(s["kind"], {"doclib", "dirlist", "linklist", "chapter"})
                self.assertIn(s["icb"], cl["icbs"])
            for n in cl["notWatched"]:
                self.assertTrue(n["what"] and len(n["reason"]) > 30)

    def test_the_three_clusters_asked_for_are_covered(self):
        icbs = {c for cl in self.cfg["clusters"] for c in cl["icbs"]}
        self.assertEqual(icbs, {"QHL", "QUA", "QWU", "QGH"})

    def test_no_customer_is_named(self):
        self.assertNotIn("ego", json.dumps(self.cfg).lower().replace("hereford", "").replace("region", ""))

    def test_stored_file_is_stamped_and_has_no_page_text(self):
        with open(os.path.join(HERE, "data", "cluster-watch.json"), encoding="utf-8") as fh:
            d = json.load(fh)
        self.assertIn("ref", d["_notice"])
        self.assertNotIn('"text"', json.dumps(d))


if __name__ == "__main__":
    unittest.main()
