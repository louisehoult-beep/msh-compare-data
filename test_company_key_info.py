#!/usr/bin/env python3
"""The company briefs behind My Hub's "What you should know".

scripts/build_company_key_info.py turns the Hub's own data files into one file
per company. A member reads these as fact, so the checks are about honesty:
every line has a real source link or a named source, nothing is dated in the
future, no fact is invented outside the data files, competitors are real other
companies, and the picker only offers companies that have something to show.
Runs on the committed output, so it needs no network.

    python3 test_company_key_info.py
"""
import glob
import json
import os
import re
import unittest
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
DIR = os.path.join(HERE, 'data', 'company-key-info')
KINDS = {'news', 'tariff', 'discontinued', 'share', 'framework', 'formulary', 'award'}


def load_all():
    index = json.load(open(os.path.join(DIR, 'index.json'), encoding='utf-8'))
    files = {}
    for p in glob.glob(os.path.join(DIR, '*.json')):
        name = os.path.basename(p)[:-5]
        if name != 'index':
            files[name] = json.load(open(p, encoding='utf-8'))
    return index, files


def every_fact(d):
    for f in d['head'] + d['f']:
        yield f
    for c in d['comp']:
        for f in c['f']:
            yield f


class CompanyKeyInfo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index, cls.files = load_all()

    def test_picker_matches_files_exactly(self):
        ids = [c['id'] for c in self.index['companies']]
        self.assertEqual(sorted(ids), sorted(self.files), 'the picker must offer exactly the companies that have a file')
        self.assertEqual(len(ids), len(set(ids)))

    def test_ids_are_what_the_account_accepts(self):
        for cid in self.files:
            self.assertRegex(cid, r'^[a-z0-9-]{1,80}$', cid)

    def test_every_company_has_something_to_show(self):
        for cid, d in self.files.items():
            self.assertTrue(d['f'], cid + ' has no facts and should not be offered')
            self.assertEqual(d['id'], cid)

    def test_facts_are_well_formed_and_sourced(self):
        for cid, d in self.files.items():
            for f in every_fact(d):
                self.assertIn(f['k'], KINDS, cid)
                self.assertTrue(f['t'].strip(), cid)
                self.assertTrue(f.get('u') or f.get('s'), cid + ': "' + f['t'] + '" has neither a link nor a named source')
                if f.get('u'):
                    self.assertRegex(f['u'], r'^https?://\S+$', cid)
                self.assertFalse(any(k.startswith('_') for k in f), cid + ' leaks an internal key')

    def test_awards_are_recent_sourced_and_linked(self):
        n = 0
        for cid, d in self.files.items():
            for f in every_fact(d):
                if f['k'] == 'award':
                    n += 1
                    self.assertTrue(f.get('u', '').startswith('http'), cid)
                    self.assertTrue(f.get('d'), cid)
        self.assertGreater(n, 0)

    def test_no_future_dates(self):
        # framework entries carry their END date in d, so only dated news-like kinds are held to today
        today = date.today().isoformat()
        for cid, d in self.files.items():
            for f in every_fact(d):
                if f['k'] in ('news', 'tariff', 'discontinued', 'formulary') and f.get('d'):
                    self.assertLessEqual(f['d'][:10], today, cid + ': ' + f['t'])

    def test_headlines_are_a_subset_of_facts_and_capped(self):
        for cid, d in self.files.items():
            self.assertLessEqual(len(d['head']), 4)
            titles = {f['t'] for f in d['f']}
            for h in d['head']:
                self.assertIn(h['t'], titles, cid)

    def test_competitors_are_other_real_companies(self):
        for cid, d in self.files.items():
            self.assertLessEqual(len(d['comp']), 4)
            for c in d['comp']:
                self.assertNotEqual(c['id'], cid, cid + ' lists itself as a competitor')
                self.assertIn(c['id'], self.files, cid + ' names a competitor with no file')
                self.assertTrue(c['f'], cid + ' lists ' + c['n'] + ' with nothing to say about it')

    def test_no_confidential_member_or_call_material(self):
        banned = re.compile(r'consultancy|IQVIA|logged in|VAT receipt|prep sheet|Aneeka', re.I)
        for cid, d in self.files.items():
            for f in every_fact(d):
                self.assertIsNone(banned.search(f['t'] + ' ' + f.get('x', '')), cid + ': ' + f['t'])

    def test_ego_brief_matches_the_hub_dermatology_panel(self):
        d = self.files.get('ego-pharmaceuticals-uk')
        self.assertIsNotNone(d, 'Ego must have a brief: it is the first company this was built for')
        panel = json.load(open(os.path.join(HERE, 'data', 'speciality-panels', 'dermatology.json'), encoding='utf-8'))
        qv = [b for b in panel['marketShare']['markets'][0]['primary']['brands'] if b['brand'] == 'QV'][0]
        share = [f for f in d['f'] if f['k'] == 'share'][0]
        self.assertIn(str(qv['share']) + '%', share['t'], 'QV share on the brief must equal the panel')
        names = [f['t'] for f in d['f'] if f['k'] == 'discontinued']
        self.assertTrue(any('QV 5% skin lotion' in n for n in names))
        comp = {c['n'] for c in d['comp']}
        self.assertTrue({'Aspire Pharma', 'Dermal Laboratories Ltd'} <= comp, 'the two biggest emollient brands must be named competitors')


if __name__ == '__main__':
    unittest.main()
