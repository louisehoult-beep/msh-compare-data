#!/usr/bin/env python3
"""Private company desks must never reach the public Hub search index.

Added 18/11/2026. Page 6259 (Meril UK) and page 6502 (Medilogik) are desks
restricted to one client's team. They were in data/hub-search-index.json, a
PUBLIC file, so any member's search and anyone reading the raw GitHub URL could
see they exist and what they cover.

    python3 test_search_private_desks.py
"""
import importlib.util
import json
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


BSE = _load("bse_private", "build_search_index.py")


def page(pid, slug, title, body="<h2>Section heading</h2><p>Several words of real content live here today.</p>"):
    return {"id": pid, "title": {"raw": title}, "content": {"raw": body},
            "link": "https://medsalesintelligencehub.co.uk/medical-sales-hub/%s/" % slug}


class PrivateDesks(unittest.TestCase):
    def test_constant_lists_both_desks(self):
        self.assertEqual(BSE.PRIVATE_DESKS.get(6259), "meril-uk")
        self.assertEqual(BSE.PRIVATE_DESKS.get(6502), "medilogik")

    def test_build_never_indexes_a_desk(self):
        pages = [page(6259, "meril-uk", "Meril UK"), page(6502, "medilogik", "Medilogik"),
                 page(1234, "urology", "Urology")]
        doc = BSE.build(pages)
        ids = [p["id"] for p in doc["pages"]]
        self.assertEqual(ids, [1234])

    def test_slug_alone_is_enough(self):
        # A desk re-created under a new page id is still caught by its path.
        doc = BSE.build([page(88888, "meril-uk", "Meril UK desk"), page(1234, "urology", "Urology")])
        self.assertEqual([p["id"] for p in doc["pages"]], [1234])

    def test_public_supplier_record_survives(self):
        doc = BSE.build([page(1234, "urology", "Urology")])
        names = [r["t"] for r in doc["records"]]
        self.assertTrue(any(n.startswith("Meril UK") for n in names), "public supplier record must stay")

    def test_shipped_index_is_clean(self):
        d = json.load(open(os.path.join(HERE, "data", "hub-search-index.json")))
        for p in d["pages"]:
            self.assertNotIn(p["id"], BSE.PRIVATE_DESK_IDS)
            self.assertFalse(BSE.is_private_desk(p["id"], p["u"]), p["u"])
        for r in d["records"]:
            self.assertFalse(BSE.is_private_desk(None, r["u"].split("#")[0]), r["u"])


if __name__ == "__main__":
    unittest.main()
