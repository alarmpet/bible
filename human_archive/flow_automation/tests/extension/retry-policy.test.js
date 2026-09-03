import assert from 'node:assert/strict';
import test from 'node:test';
import { classifyFailure, randomDelayMs } from '../../extension/core/retry-policy.js';

test('paid credit and ambiguous result always pause', () => {
  for (const code of ['CREDIT_PURCHASE_REQUIRED', 'AMBIGUOUS_RESULT', 'CAPTCHA', 'PROJECT_MISMATCH']) assert.equal(classifyFailure(code, 1, 2), 'pause');
});
test('transient failures retry until the limit, then pause', () => {
  assert.equal(classifyFailure('NETWORK_ERROR', 1, 2), 'retry');
  assert.equal(classifyFailure('NETWORK_ERROR', 3, 2), 'pause');
  assert.equal(classifyFailure('UNKNOWN', 1, 2), 'pause');
});
test('delay is inclusive and uses supplied crypto source', () => {
  assert.equal(randomDelayMs(5000, 15000, (v) => { v[0] = 0; }), 5000);
  assert.equal(randomDelayMs(5000, 15000, (v) => { v[0] = 0xffffffff; }), 15000);
});
