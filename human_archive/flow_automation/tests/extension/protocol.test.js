import test from 'node:test';
import assert from 'node:assert/strict';

async function loadProtocol() {
  return import('../../extension/core/protocol.js');
}

function validMessage() {
  return {
    protocol_version: 1,
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


test('rejects missing required envelope fields', async () => {
  const { validateEnvelope } = await loadProtocol();
  for (const field of ['message_id', 'job_id', 'type', 'payload', 'protocol_version']) {
    const message = validMessage();
    delete message[field];
    assert.throws(() => validateEnvelope(message), new RegExp(field));
  }
});

test('requires protocol_version and rejects schema_version in an envelope', async () => {
  const { validateEnvelope } = await loadProtocol();
  assert.throws(() => validateEnvelope({ ...validMessage(), protocol_version: undefined }), /protocol_version/);
  assert.throws(() => validateEnvelope({ ...validMessage(), schema_version: 1 }), /Unknown envelope field|protocol_version/);
});

test('uses the canonical message-type resource', async () => {
  const { MESSAGE_TYPES } = await loadProtocol();
  const { default: messageTypes } = await import('../../extension/shared/message_types.json', {
    with: { type: 'json' },
  });
  assert.deepEqual([...MESSAGE_TYPES].sort(), [...messageTypes].sort());
  assert.equal(MESSAGE_TYPES.size, 15);
});
