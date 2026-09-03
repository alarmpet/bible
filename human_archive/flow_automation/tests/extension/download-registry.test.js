import assert from 'node:assert/strict';
import test from 'node:test';
import { DownloadRegistry } from '../../extension/core/download-registry.js';

test('completion preserves shot and prompt identity', () => { const registry = new DownloadRegistry(); registry.register(42, { jobId: 'j1', shotId: 'SHOT_001', promptSha256: 'a'.repeat(64), attempt: 1 }); const result = registry.complete(42, 'C:/Downloads/NOLLAM/j1/SHOT_001__aaaaaaaa.png'); assert.equal(result.shotId, 'SHOT_001'); assert.equal(result.promptSha256, 'a'.repeat(64)); });
test('unknown download id cannot advance the queue', () => assert.throws(() => new DownloadRegistry().complete(99, 'x.png'), /unknown download/));
test('wrong filename pauses instead of accepting', () => { const registry = new DownloadRegistry(); registry.register(7, { jobId: 'j1', shotId: 'SHOT_001', promptSha256: 'b'.repeat(64), attempt: 1 }); assert.equal(registry.complete(7, 'SHOT_002__bbbbbbbb.png').code, 'DOWNLOAD_FILENAME_MISMATCH'); });
test('restore pauses incomplete downloads', async () => { const registry = new DownloadRegistry(); registry.register(8, { jobId: 'j1', shotId: 'SHOT_001', promptSha256: 'c'.repeat(64), attempt: 1 }); const rows = await registry.restore(async () => ({ state: 'interrupted' })); assert.equal(rows[0].code, 'DOWNLOAD_INTERRUPTED'); });
