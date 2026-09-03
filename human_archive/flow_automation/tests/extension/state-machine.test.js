import assert from 'node:assert/strict';
import test from 'node:test';
import { transition } from '../../extension/core/state-machine.js';

test('accepts legal transitions', () => { assert.equal(transition('IDLE', 'PREFLIGHT'), 'PREFLIGHT'); assert.equal(transition('VALIDATING', 'SHOT_ACCEPTED'), 'ACCEPTED'); });
test('rejects illegal transitions', () => { assert.throws(() => transition('IDLE', 'SHOT_ACCEPTED'), /Illegal transition/); });
test('state objects preserve metadata', () => { assert.deepEqual(transition({ status: 'READY', shot_id: 'SHOT_001' }, { type: 'SHOT_SUBMITTED' }), { status: 'SUBMITTING', shot_id: 'SHOT_001' }); });
