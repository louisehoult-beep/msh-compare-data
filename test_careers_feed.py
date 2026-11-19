"""Live Desk Careers feed (scripts/careers_feed.py). Run: python3 -m unittest test_careers_feed"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts"))
import careers_feed as cf  # noqa: E402
import careers_relevance  # noqa: E402

SPECS = [{"slug": "ophthalmology", "label": "Ophthalmology"},
         {"slug": "orthopaedics-and-trauma", "label": "Orthopaedics and Trauma"}]


def role(title, location, **kw):
    return {"title": title, "location": location, "uk": True, "url": "https://x.example/" + title.replace(" ", "-"), **kw}


class Regions(unittest.TestCase):
    def test_title_territory_beats_head_office(self):
        self.assertEqual(cf.regions_of(role("Senior Key Account Manager ( Wales)", "United Kingdom - Maidenhead")), ["wales"])

    def test_location_used_when_title_is_silent(self):
        self.assertEqual(cf.regions_of(role("Contract Manager", "Crawley")), ["south-east"])
        self.assertEqual(cf.regions_of(role("Account Manager", "United Kingdom-Dundee")), ["scotland"])

    def test_bare_north_or_uk_is_not_guessed(self):
        self.assertEqual(cf.regions_of(role("Territory Manager - North", "United Kingdom")), [])
        self.assertEqual(cf.regions_of(role("Virtual Territory Manager", "3 Locations")), [])

    def test_two_areas_kept(self):
        self.assertEqual(cf.regions_of(role("Territory Manager (London & South East)", "2 Locations")), ["london", "south-east"])
        self.assertEqual(cf.regions_of(role("Clinical Specialist - Midlands", "United Kingdom")), ["east-midlands", "west-midlands"])

    def test_wales_inside_new_south_wales_is_dropped(self):
        self.assertIsNone(cf.regions_of(role("IOL Manager, NSW West", "Remote - New South Wales")))

    def test_new_york_is_not_york(self):
        self.assertIsNone(cf.regions_of(role("Rep", "New York")))


class Matching(unittest.TestCase):
    R = {"regions": ["scotland"], "specialities": ["ophthalmology"]}

    def test_empty_choice_matches(self):
        self.assertTrue(cf.matches(self.R, [], []))

    def test_other_area_does_not(self):
        self.assertFalse(cf.matches(self.R, ["london"], []))

    def test_unstated_area_and_speciality_not_excluded(self):
        self.assertTrue(cf.matches({"regions": [], "specialities": []}, ["london"], ["orthopaedics-and-trauma"]))

    def test_wrong_speciality(self):
        self.assertFalse(cf.matches(self.R, [], ["orthopaedics-and-trauma"]))


class Building(unittest.TestCase):
    def test_build_and_new(self):
        compiled = careers_relevance.load_config()
        doc = {"generatedOn": "2026-10-27", "suppliers": [
            {"name": "Alcon Eye Care UK", "checkedOn": "2026-10-27", "roles": [
                role("Territory Manager - South West", "Remote - England", new=True),
                role("Territory Manager Elsewhere", "Remote - New South Wales")]}]}
        idx = {"suppliers": [{"name": "Alcon Eye Care UK", "specialities": ["Ophthalmology", "Unmapped thing"]}]}
        out = cf.build(doc, idx, SPECS, compiled, today="2026-10-27")
        self.assertEqual(out["count"], 1)
        r = out["roles"][0]
        self.assertEqual((r["regions"], r["specialities"], r["company"]), (["south-west"], ["ophthalmology"], "Alcon Eye Care UK"))
        self.assertEqual(cf.new_roles(out, None), [])            # first publish: no alerts
        self.assertEqual(cf.new_roles(out, {"roles": []}), out["roles"])
        self.assertEqual(cf.new_roles(out, {"roles": [{"url": r["url"]}]}), [])

    def test_message(self):
        m = cf.role_message([{"title": "T", "company": "C", "location": "L", "url": "https://u"}] * 3)
        self.assertEqual(m["title"], "New roles on the Live Desk")
        self.assertIn("and 2 more", m["body"])


if __name__ == "__main__":
    unittest.main()
