import assert from 'node:assert/strict';
import test from 'node:test';
import fs from 'node:fs';
import path from 'node:path';
const root = path.resolve(import.meta.dirname, '../../extension');
const manifest = JSON.parse(fs.readFileSync(path.join(root, 'manifest.json'), 'utf8'));
test('requests only the approved MV3 permissions', () => {
  assert.deepEqual(new Set(manifest.permissions), new Set(['storage','downloads','sidePanel','nativeMessaging','scripting','tabs']));
  assert.deepEqual(manifest.host_permissions, ['https://labs.google/*']);
  assert.equal(manifest.permissions.includes('debugger'), false);
  assert.equal(manifest.permissions.includes('<all_urls>'), false);
});
test('runs only on Flow project pages', () => {
  assert.deepEqual(manifest.content_scripts[0].matches, ['https://labs.google/*/tools/flow/project/*']);
});
