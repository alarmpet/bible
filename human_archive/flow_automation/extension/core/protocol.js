const CANONICAL_MESSAGE_TYPES = [
  "HELLO",
  "LOAD_JOB",
  "JOB_START_REQUESTED",
  "SHOT_SUBMITTED",
  "SHOT_RESULT_FOUND",
  "DOWNLOAD_STARTED",
  "DOWNLOAD_COMPLETED",
  "SHOT_FAILED",
  "JOB_STOPPED",
  "JOB_STATE",
  "RUN_SHOT",
  "SHOT_ACCEPTED",
  "SHOT_RETRY",
  "JOB_PAUSED",
  "JOB_COMPLETED"
];

const MESSAGE_TYPES = new Set(CANONICAL_MESSAGE_TYPES);
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
const ALLOWED_KEYS = new Set(['protocol_version', 'message_id', 'type', 'job_id', 'payload']);

function protocolError(message) {
  return new TypeError(message);
}

function isPlainObject(value) {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function validateEnvelope(value, expectedJobId) {
  if (!isPlainObject(value)) throw protocolError('message must be an object');
  for (const key of Object.keys(value)) {
    if (!ALLOWED_KEYS.has(key)) throw protocolError(`Unknown envelope field: ${key}`);
  }
  if (value.protocol_version !== 1) throw protocolError('protocol_version must equal 1');
  if (typeof value.message_id !== 'string' || !UUID_PATTERN.test(value.message_id)) throw protocolError('message_id must be a UUID');
  if (typeof value.type !== 'string' || !MESSAGE_TYPES.has(value.type)) throw protocolError('type must be an allowlisted message type');
  if (typeof value.job_id !== 'string' || value.job_id.trim() === '') throw protocolError('job_id must be non-empty');
  if (!isPlainObject(value.payload)) throw protocolError('payload must be an object');
  const normalizedJobId = value.job_id.trim();
  if (expectedJobId !== undefined && expectedJobId !== null && normalizedJobId !== String(expectedJobId).trim()) throw protocolError('job_id does not match expectedJobId');
  return { protocol_version: 1, message_id: value.message_id, type: value.type, job_id: normalizedJobId, payload: { ...value.payload } };
}

function makeEnvelope(type, jobId, payload, messageId = globalThis.crypto.randomUUID()) {
  return validateEnvelope({ protocol_version: 1, message_id: messageId, type, job_id: jobId, payload });
}

export { MESSAGE_TYPES, validateEnvelope, makeEnvelope };
