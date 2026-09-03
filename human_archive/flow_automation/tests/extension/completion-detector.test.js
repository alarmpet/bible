import assert from 'node:assert/strict';
import test from 'node:test';
import { identifyCompletedCard, preflight } from '../../extension/content/completion-detector.js';

function image(id = 'media-3', width = 1920, height = 1080) { return { naturalWidth: width, naturalHeight: height, dataset: { mediaIdentity: id } }; }
function card(id, media = image(), extra = {}) { return { id, dataset: { cardId: id, mediaIdentity: media.dataset.mediaIdentity, stableObservations: '2', ...extra }, querySelector: () => media }; }
function doc(cards = [], busy = false, editor = true) { return { querySelectorAll: (selector) => selector.includes('generation-card') ? cards : [], querySelector: (selector) => selector.includes('progressbar') && busy ? {} : selector.includes('textbox') && editor ? {} : null }; }

test('returns only the unique new stable card', () => assert.deepEqual(identifyCompletedCard(doc([card('old-1'), card('old-2'), card('new-3')]), { cardIds: ['old-1', 'old-2'] }), { status: 'complete', cardId: 'new-3', mediaIdentity: 'media-3', width: 1920, height: 1080 }));
test('never chooses ambiguous new cards', () => assert.equal(identifyCompletedCard(doc([card('old-1'), card('new-2'), card('new-3')]), { cardIds: ['old-1'] }).code, 'AMBIGUOUS_RESULT'));
test('busy and changed UI fail closed', () => { assert.equal(identifyCompletedCard(doc([card('old')], true), { cardIds: ['old'] }).status, 'pending'); assert.equal(identifyCompletedCard(doc(), {}).code, 'FLOW_UI_CHANGED'); });
test('preflight verifies exact project and image mode', () => { const job = { project: { expected_url: 'https://labs.google/fx/tools/flow/project/p1' }, media_type: 'image' }; assert.equal(preflight(doc([card('old')]), { href: job.project.expected_url }, job).ok, true); assert.equal(preflight(doc([card('old')]), { href: 'https://labs.google/fx/tools/flow/project/other' }, job).code, 'PROJECT_MISMATCH'); });
