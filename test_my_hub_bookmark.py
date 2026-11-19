"""My Hub bookmark prompt: shown once, says which site this is, dismiss is remembered."""
import re
import unittest

JS = open('app/my-hub.js', encoding='utf-8').read()


class Bookmark(unittest.TestCase):
    def test_prompt_exists_and_names_the_site(self):
        self.assertIn('Bookmark My Hub', JS)
        self.assertIn('not the Elevate &amp; Thrive training site', JS)

    def test_dismiss_is_remembered_and_wired(self):
        self.assertRegex(JS, r"act === 'bm-dismiss'")
        self.assertIn("localStorage.setItem(LS_BM", JS)
        self.assertIn("bmHtml()", JS)

    def test_storage_failure_hides_prompt(self):
        self.assertRegex(JS, r"function bmSeen\(\)[^\n]*catch \(e\) \{ return true; \}")


if __name__ == '__main__':
    unittest.main()
