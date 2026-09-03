const RETRYABLE = new Set([
  'NETWORK_ERROR', 'GENERATION_FAILED', 'DOWNLOAD_FAILED', 'IMAGE_DECODE_FAILED',
  'PARTIAL_DOWNLOAD', 'TRANSIENT_ERROR', 'TIMEOUT',
]);

const PAUSE = new Set([
  'AUTH_REQUIRED', 'AUTHENTICATION_REQUIRED', 'CAPTCHA', 'CREDIT_PURCHASE_REQUIRED',
  'MODE_MISMATCH', 'PROJECT_MISMATCH', 'AMBIGUOUS_RESULT', 'AMBIGUOUS_ATTRIBUTION',
  'SELECTOR_CHANGED', 'EXTENSION_UPDATE', 'EXHAUSTED',
]);

function classifyFailure(code, attempt, retryLimit) {
  if (!Number.isInteger(attempt) || attempt < 1 || !Number.isInteger(retryLimit) || retryLimit < 0) return 'pause';
  if (PAUSE.has(code) || attempt > retryLimit) return 'pause';
  return RETRYABLE.has(code) ? 'retry' : 'pause';
}

function randomDelayMs(minMs = 5000, maxMs = 15000, randomValues = globalThis.crypto?.getRandomValues?.bind(globalThis.crypto)) {
  if (!Number.isFinite(minMs) || !Number.isFinite(maxMs) || minMs < 0 || maxMs < minMs) throw new RangeError('invalid delay range');
  if (!randomValues) throw new Error('crypto.getRandomValues is required');
  const span = Math.floor(maxMs - minMs) + 1;
  const values = new Uint32Array(1);
  randomValues(values);
  return Math.floor(minMs + (values[0] / 0x100000000) * span);
}

export { RETRYABLE, PAUSE, classifyFailure, randomDelayMs };
