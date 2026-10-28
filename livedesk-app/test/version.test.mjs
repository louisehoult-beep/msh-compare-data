import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

// The stores read the version from the native projects, not package.json.
// Live Desk 1.1.0 was tagged with both still at 1.0.2, so the release went out
// under the old number (or was refused by App Store Connect).
const read = (p) => readFileSync(new URL(p, import.meta.url), 'utf8');
const pkg = JSON.parse(read('../package.json')).version;

test('iOS MARKETING_VERSION matches package.json', () => {
  const found = [...read('../ios/App/App.xcodeproj/project.pbxproj').matchAll(/MARKETING_VERSION = ([^;]+);/g)].map((m) => m[1]);
  assert.ok(found.length > 0);
  for (const v of found) assert.equal(v, pkg);
});

test('Android versionName matches package.json', () => {
  assert.equal(read('../android/app/build.gradle').match(/versionName "([^"]+)"/)[1], pkg);
});
