import { test } from 'node:test';
import assert from 'node:assert/strict';
import { filterFeed, itemsFromNotification, newCount, passFromLink, safeUrl, shortDate, stamp } from '../src/logic.js';

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
