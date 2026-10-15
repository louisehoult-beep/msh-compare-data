#!/usr/bin/env python3
"""Invariants for scripts/redact_personal.py.

Added 29/09/2026. The redactor strips every phone-shaped number from a named
person's note, and a phone shape is anything starting with 0. That turned
"registration number 0450787886" (NTI9 LLC, a New Jersey company that was a
corporate director) into "registration number [phone withheld]" on every
supplier-index rebuild: a company identifier lost, and a label that says it was
a phone number. A number the text itself labels as a registration or company
number is an identifier, not a contact route, so it stays.

The other half matters as much: a real phone in a person's note must still go.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts"))
from redact_personal import (redact_obj, redact_text, unattributed_person_emails,  # noqa: E402
                             PUBLISHED_MARKER, DATA_PROTECTION)


class LabelledIdentifiersSurvive(unittest.TestCase):
    def test_nti9_registration_number(self):
        note = ("A New Jersey limited liability company, registration number 0450787886, "
                "of Suite 208, 1770 W County Line Road, Lakewood, New Jersey.")
        self.assertEqual(redact_text(note, strip_all_phones=True), note)

    def test_other_labels(self):
        for label in ("company number", "Company No.", "registered number",
                      "registration no:", "charity number", "Companies House number"):
            s = "%s 01234567 filed" % label
            self.assertEqual(redact_text(s, strip_all_phones=True), s, label)

    def test_via_redact_obj_people_note(self):
        doc = {"people": [{"name": "NTI9 LLC",
                           "note": "registration number 0450787886, held 50-75%"}]}
        out = redact_obj(doc)
        self.assertIn("0450787886", out["people"][0]["note"])


class RealPhonesStillGo(unittest.TestCase):
    def test_phone_in_person_note(self):
        s = "Direct line 01722 336262, mobile 07584 538719."
        out = redact_text(s, strip_all_phones=True)
        self.assertNotIn("336262", out)
        self.assertNotIn("538719", out)

    def test_phone_after_label_elsewhere_in_sentence(self):
        # "number" alone is not a registration label: "call on number 0208 296 4692"
        s = "Call her on number 0208 296 4692."
        self.assertNotIn("4692", redact_text(s, strip_all_phones=True))

    def test_trailing_phone_after_person_email(self):
        s = "ann.hamed@cht.nhs.uk, 07584538719"
        out = redact_text(s)
        self.assertNotIn("07584538719", out)
        self.assertNotIn("ann.hamed", out)



class PublishedEmailsKeptAndAttributed(unittest.TestCase):
    """14/10/2026, Lou: an email the organisation itself published may stay,
    with a note naming the publisher and a data protection statement."""
    TEXT = "Site visits: jane.smith@leedsth.nhs.uk, 0113 243 3144, or procurement@leedsth.nhs.uk."

    def test_kept_with_publisher_and_statement(self):
        out = redact_text(self.TEXT, published_by="Leeds Teaching Hospitals NHS Trust")
        self.assertIn("jane.smith@leedsth.nhs.uk", out)
        self.assertIn(PUBLISHED_MARKER + "Leeds Teaching Hospitals NHS Trust.", out)
        self.assertIn(DATA_PROTECTION, out)
        self.assertNotIn("3144", out)            # the ruling covered emails, not phones
        self.assertIn("procurement@leedsth.nhs.uk", out)

    def test_no_publisher_still_withheld(self):
        out = redact_text(self.TEXT)
        self.assertNotIn("jane.smith", out)
        self.assertNotIn(PUBLISHED_MARKER, out)

    def test_no_person_email_no_note(self):
        s = "Contact procurement@leedsth.nhs.uk."
        self.assertEqual(redact_text(s, published_by="Leeds"), s)

    def test_later_blanket_pass_keeps_attributed_text(self):
        # build_supplier_index.py runs redact_obj over everything as a last pass.
        kept = redact_text(self.TEXT, published_by="Leeds Teaching Hospitals NHS Trust")
        doc = {"suppliers": [{"note": kept}]}
        self.assertEqual(redact_obj(doc)["suppliers"][0]["note"], kept)

    def test_gate_fails_only_unattributed(self):
        kept = redact_text(self.TEXT, published_by="Leeds Teaching Hospitals NHS Trust")
        self.assertEqual(unattributed_person_emails({"a": kept}), [])
        self.assertEqual(unattributed_person_emails({"a": kept, "b": self.TEXT}),
                         ["jane.smith@leedsth.nhs.uk"])


if __name__ == "__main__":
    r = unittest.main(exit=False, verbosity=1).result
    print("REDACTOR HOLDS" if r.wasSuccessful() else "REDACTOR BROKEN")
    sys.exit(0 if r.wasSuccessful() else 1)
