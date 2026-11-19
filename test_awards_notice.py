#!/usr/bin/env python3
"""
test_awards_notice.py — prove scripts/refresh_awards.py's own write cannot leave
the gate red, and cannot reformat the file it writes.

WHY THIS EXISTS (17/11/2026). refresh_awards.write() used a plain
json.dump(indent=1). assemble() builds the document from scratch, so that write
dropped data/company-awards.json's `_notice` block and verify.py's check_notice()
then failed the publish with

    [notice] data/company-awards.json is missing its ownership notice

It bit twice in one day: a `--rematch` run after a seed edit dropped the notice,
the next gate went red, and a separate `scripts/stamp_notice.py` run was needed
to clear it. write() now stamps the notice itself, first key, and writes through
seed_format.write_like() so it keeps the file's own byte format instead of
asserting one.

  python3 test_awards_notice.py     exit 0 = pass. Stdlib only.
"""

import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "scripts"))
import refresh_awards as ra      # noqa: E402
import seed_format               # noqa: E402
import stamp_notice              # noqa: E402

AWARDS = "company-awards.json"


def read(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


class WriteIsStamped(unittest.TestCase):

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, AWARDS)
        self.addCleanup(shutil.rmtree, self.dir)

    def test_notice_is_stamped_on_a_document_that_has_none(self):
        ra.write({"counts": {"companies": 0}}, self.path)
        doc = read(self.path)
        self.assertEqual(doc["_notice"], stamp_notice.notice_for(AWARDS))

    def test_notice_is_the_first_key_so_stamp_notice_agrees(self):
        ra.write({"counts": {"companies": 0}}, self.path)
        self.assertEqual(list(read(self.path))[0], "_notice")

    def test_a_second_write_is_a_no_op_for_stamp_notice(self):
        """What the gate actually asks: after this writer, is the file stamped
        with the CURRENT notice? A drifted notice fails exactly as a missing one
        does, so compare the whole block, not just its presence."""
        ra.write({"counts": {"companies": 1}}, self.path)
        doc = read(self.path)
        self.assertEqual(doc.get("_notice"), stamp_notice.notice_for(AWARDS))
        # An inherited stale notice must not survive either.
        stale = dict(stamp_notice.notice_for(AWARDS))
        stale["copyright"] = "© Someone Else 1999"
        ra.write({"_notice": stale, "counts": {"companies": 2}}, self.path)
        self.assertEqual(read(self.path)["_notice"],
                         stamp_notice.notice_for(AWARDS))

    def test_the_existing_byte_format_is_kept_not_asserted(self):
        """data/company-awards.json is indent 1 with no trailing newline today,
        but nothing here may assert that: a hardcoded style is what reformatted
        9.6MB elsewhere, and a whole-file diff in this repo IS the review
        disappearing."""
        for fmt in (seed_format.Format(1, False),
                    seed_format.Format(2, True),
                    seed_format.Format(None, False)):
            with self.subTest(fmt=repr(fmt)):
                seeded = {"_notice": stamp_notice.notice_for(AWARDS), "counts": {}}
                with open(self.path, "wb") as fh:
                    fh.write(fmt.dumps(seeded))
                ra.write({"counts": {"companies": 3}}, self.path)
                with open(self.path, "rb") as fh:
                    raw = fh.read()
                self.assertEqual(seed_format.detect(raw), fmt)

    def test_an_unreffed_filename_is_not_given_an_invented_notice(self):
        other = os.path.join(self.dir, "not-a-data-file.json")
        ra.write({"counts": {}}, other)
        self.assertNotIn("_notice", read(other))


if __name__ == "__main__":
    unittest.main(verbosity=2)
