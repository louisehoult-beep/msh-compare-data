#!/usr/bin/env python3
"""Sofia: an item the runner cannot re-read is kept only if it was verified earlier today."""
import copy, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scripts'))
import refresh_sofia_insights as r

URL = 'https://www.england.nhs.uk/x/'
CFG = [{'id': 's', 'area': 'Supplier duties', 'title': 't', 'summary': 'u', 'meaning': 'm',
        'evidence': [{'name': 'n', 'url': URL, 'quotes': ['q']}]}]
TODAY = r.TODAY.isoformat()
OLD = {'id': 's', 'type': 'standing', 'area': 'Supplier duties', 'title': 't', 'summary': 'u', 'meaning': 'm',
       'sources': [{'name': 'n', 'url': URL}], 'verifiedOn': TODAY}
NEW = {'id': 'n-a', 'type': 'new', 'sources': [{'name': 'n', 'url': URL}], 'verifiedOn': TODAY}
BLOCKED = {'www.england.nhs.uk'}


def run(items, current=(), unreadable=('s',), blocked=BLOCKED, as_of=TODAY, cfg=CFG):
    prev = {'dataAsOf': as_of, 'items': items}
    return [i['id'] for i in r.carry_today(prev, cfg, set(current), set(unreadable), set(blocked))]


assert run([OLD, NEW]) == ['s', 'n-a']
assert run([dict(OLD, verifiedOn='2000-01-01')]) == [], 'an earlier day is never kept'
assert run([OLD], as_of='2000-01-01') == []
assert run([OLD], unreadable=()) == [], 'read but quote gone: held'
assert run([OLD], current=('s',)) == [], 'no duplicate'
changed = copy.deepcopy(CFG); changed[0]['summary'] = 'different'
assert run([OLD], cfg=changed) == [], 'changed words need a fresh read'
assert run([OLD], cfg=[]) == [], 'removed item is not kept'
assert run([NEW], blocked=()) == []
assert r.carry_today(None, CFG, set(), {'s'}, BLOCKED) == []


class Empty202:
    status = 202
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def read(self): return b''


calls = []
r.urllib.request.urlopen = lambda *a, **k: calls.append(1) or Empty202()
for _ in range(2):
    try:
        r.fetch(URL)
        raise AssertionError('empty 202 accepted')
    except r.Unreadable:
        pass
assert len(calls) == 1, 'a declining site is asked once'
print('test_sofia_carry: OK')
