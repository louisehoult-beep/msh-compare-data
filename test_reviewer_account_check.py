import datetime as dt
import sys
import unittest

sys.path.insert(0, "scripts")
from reviewer_account_check import faults_for

NOW = dt.datetime(2026, 11, 4, tzinfo=dt.timezone.utc)
OK_USER = {"email_confirmed_at": "2026-11-04T20:00:00Z"}
OK_ACCESS = {"store_expires_at": "2027-12-31T23:59:59Z"}
OK_MEMBER = {"status": "approved"}


class ReviewerAccount(unittest.TestCase):
    def test_fit_for_review(self):
        assert faults_for(OK_USER, OK_ACCESS, OK_MEMBER, NOW) == []


    def test_state_found_on_04_11_is_caught(self):
        f = faults_for({"email_confirmed_at": None}, None, OK_MEMBER, NOW)
        assert any("not confirmed" in x for x in f) and any("paywall" in x for x in f)


    def test_missing_account(self):
        assert faults_for(None, None, None, NOW) == ["account does not exist"]


    def test_access_about_to_end(self):
        f = faults_for(OK_USER, {"store_expires_at": "2026-11-10T00:00:00Z"}, OK_MEMBER, NOW)
        assert any("under 14 days" in x for x in f)


    def test_banned_and_no_membership(self):
        f = faults_for({**OK_USER, "banned_until": "2030-01-01T00:00:00Z"}, OK_ACCESS, None, NOW)
        assert any("banned" in x for x in f) and any("Industry Nurses" in x for x in f)


if __name__ == "__main__":
    unittest.main()
