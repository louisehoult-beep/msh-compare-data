import { test } from 'node:test';
import assert from 'node:assert/strict';
import { filterCareers, rankCareers, deskTheme, filterFeed, topStories, itemsFromNotification, newCount, passFromLink, safeUrl, shortDate, stamp } from '../src/logic.js';

const FEED = { panels: [
  { key: 'MHRA ALERTS', rows: [
    { kind: 'item', title: 'A', specialities: ['stroke'], new: true },
    { kind: 'item', title: 'B', specialities: [] },
    { kind: 'note', title: 'note' },
  ] },
  { key: 'NICE GUIDANCE', rows: [{ kind: 'item', title: 'C', specialities: ['urology'] }] },
] };

test('dates', () => {
  assert.equal(shortDate('2026-10-01'), '1 Oct');
  assert.equal(shortDate('nope'), '');
  assert.equal(stamp('2026-10-01T09:35:00Z'), '1 Oct, 10:35');
});

test('pass from the Hub link', () => {
  assert.equal(passFromLink('uk.co.medsalesintelligencehub.livedesk://link?pass=abc_1.def-2'), 'abc_1.def-2');
  assert.equal(passFromLink('uk.co.medsalesintelligencehub.livedesk://link?pass=<script>'), null);
  assert.equal(passFromLink('https://evil.example/link?pass=a.b'), null);
});

test('filter by speciality', () => {
  assert.equal(filterFeed(FEED, []).length, 2);
  const f = filterFeed(FEED, ['stroke']);
  assert.deepEqual(f.map((p) => p.rows.map((r) => r.title)), [['A']]);
  assert.equal(newCount(f), 1);
});

test('safe urls and notification items', () => {
  assert.equal(safeUrl('javascript:alert(1)'), '');
  assert.equal(safeUrl('https://x.org'), 'https://x.org');
  assert.deepEqual(itemsFromNotification({ items: '[{"t":"x","u":"https://a"}]' }), [{ t: 'x', u: 'https://a' }]);
  assert.deepEqual(itemsFromNotification({ items: '{bad' }), []);
});

test('desk look per panel', () => {
  assert.equal(deskTheme({ key: 'MHRA ALERTS' }).c, 'alert');
  assert.equal(deskTheme({ title: 'TENDERS & PROCUREMENT' }).img, 'procurement');
  assert.equal(deskTheme({ title: 'NICE GUIDANCE — NEW' }).c, 'nice');
  assert.equal(deskTheme({ title: 'Something else' }).c, 'other');
});

test('top stories: lead, then new, then one per desk, no repeats', () => {
  const panels = [
    { title: 'A', rows: [{ title: 'a1', url: 'u1' }, { title: 'a2', url: 'u2', new: true }] },
    { title: 'B', rows: [{ kind: 'note', title: 'n' }, { title: 'b1', url: 'u3', lead: true }] },
  ];
  assert.deepEqual(topStories(panels).map((s) => s.row.title), ['b1', 'a2', 'a1']);
  assert.equal(topStories(panels, 2).length, 2);
});

const CAREERS = { roles: [
  { title: 'A', regions: ['scotland'], specialities: [] },
  { title: 'B', regions: ['london', 'south-east'], specialities: ['ophthalmology'] },
  { title: 'C', regions: [], specialities: ['orthopaedics-and-trauma'] },
] };

test('careers: empty choice shows everything', () => {
  assert.equal(filterCareers(CAREERS, [], []).length, 3);
});
test('careers: area filter keeps named matches and roles with no stated area', () => {
  assert.deepEqual(filterCareers(CAREERS, ['london'], []).map((r) => r.title), ['B', 'C']);
  assert.deepEqual(rankCareers(filterCareers(CAREERS, ['london'], []), ['london']).map((r) => r.title), ['B', 'C']);
});
test('careers: speciality filter never hides a role with no mapped speciality', () => {
  assert.deepEqual(filterCareers(CAREERS, [], ['ophthalmology']).map((r) => r.title), ['A', 'B']);
  assert.deepEqual(filterCareers(CAREERS, ['scotland'], ['ophthalmology']).map((r) => r.title), ['A']);
  assert.equal(filterCareers(null, [], []).length, 0);
});
