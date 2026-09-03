import assert from 'node:assert/strict';
import test from 'node:test';
import { renderModel } from '../../extension/sidepanel/index.js';
test('start is disabled on wrong project or agent/video mode', () => { const model = renderModel({ projectMatch: false, mediaMode: 'video' }); assert.equal(model.canStart, false); assert.deepEqual(model.blockers, ['PROJECT_MISMATCH', 'MEDIA_TYPE_MISMATCH']); });
test('stop remains enabled while a job is active', () => assert.equal(renderModel({ state: 'WAITING_FOR_RESULT' }).canStop, true));
test('valid missing scope can start', () => assert.equal(renderModel({ state: 'READY', projectMatch: true, mediaMode: 'image' }).canStart, true));
