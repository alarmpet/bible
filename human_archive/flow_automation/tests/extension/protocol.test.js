const test = require('node:test');
const assert = require('node:assert/strict');

async function loadProtocol() {
  return import('../../extension/core/protocol.js');
}

function validMessage() {
  return {
    schema_version: 1,
    message_id: '123e4567-e89b-42d3-a456-426614174000',
    type: 'SHOT_SUBMITTED',
    job_id: 'HIMALAYA-v1',
    payload: { shot_id: 'SHOT_001' },
  };
}

test('rejects a mismatched job id', async () => {
  const { validateEnvelope } = await loadProtocol();
  assert.throws(() => validateEnvelope(validMessage(), 'other-job'), /job_id/);
});

test('rejects page-invented message types', async () => {
  const { validateEnvelope } = await loadProtocol();
  assert.throws(
    () => validateEnvelope({ ...validMessage(), type: 'EXECUTE_SCRIPT' }),
    /type/
  );
});

test('rejects unknown envelope fields', async () => {
  const { validateEnvelope } = await loadProtocol();
  assert.throws(
    () => validateEnvelope({ ...validMessage(), route: 'page' }),
    /Unknown envelope field/
  );
});

test('builds a validated envelope', async () => {
  const { makeEnvelope } = await loadProtocol();
  assert.deepEqual(
    makeEnvelope(
      'SHOT_SUBMITTED',
      'HIMALAYA-v1',
      { shot_id: 'SHOT_001' },
      '123e4567-e89b-42d3-a456-426614174000'
    ),
    validMessage()
  );
});
