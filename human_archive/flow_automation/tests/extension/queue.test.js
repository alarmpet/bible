import assert from 'node:assert/strict';
import test from 'node:test';
import { createQueue } from '../../extension/core/queue.js';

function jobWithTwoShots() { return { job_id: 'job-1', retry_limit: 2, shots: [{ shot_id: 'SHOT_001' }, { shot_id: 'SHOT_002' }] }; }

test('does not advance until host accepts current shot', () => {
  const queue = createQueue(jobWithTwoShots());
  queue.dispatch({ type: 'SHOT_RESULT_FOUND', shot_id: 'SHOT_001' });
  assert.equal(queue.next(), null);
  queue.dispatch({ type: 'SHOT_ACCEPTED', shot_id: 'SHOT_001' });
  assert.equal(queue.next().shot_id, 'SHOT_002');
});
test('only one submitted shot can be active', () => { const queue = createQueue(jobWithTwoShots()); queue.dispatch({ type: 'SHOT_SUBMITTED', shot_id: 'SHOT_001' }); assert.throws(() => queue.dispatch({ type: 'SHOT_SUBMITTED', shot_id: 'SHOT_002' }), /one active/); });
test('stop prevents further selection', () => { const queue = createQueue(jobWithTwoShots()); queue.stop(); assert.equal(queue.next(), null); assert.equal(queue.snapshot().status, 'STOPPED'); });

