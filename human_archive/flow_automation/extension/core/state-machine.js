const LEGAL = Object.freeze({
  IDLE: ['PREFLIGHT'], PREFLIGHT: ['READY', 'PAUSED', 'STOPPED'],
  READY: ['SUBMITTING', 'RENDERING', 'STOPPED'],
  SUBMITTING: ['WAITING_FOR_RESULT', 'PAUSED', 'STOPPED'],
  WAITING_FOR_RESULT: ['RESULT_IDENTIFIED', 'RETRY_PENDING', 'PAUSED', 'STOPPED'],
  RESULT_IDENTIFIED: ['DOWNLOADING', 'PAUSED', 'STOPPED'],
  DOWNLOADING: ['VALIDATING', 'RETRY_PENDING', 'PAUSED', 'STOPPED'],
  VALIDATING: ['ACCEPTED', 'RETRY_PENDING', 'PAUSED', 'STOPPED'],
  ACCEPTED: ['DELAYING', 'RENDERING', 'COMPLETED'],
  DELAYING: ['READY', 'STOPPED'], RETRY_PENDING: ['DELAYING', 'PAUSED', 'STOPPED'],
});

const EVENT_STATE = {
  PREFLIGHT: 'PREFLIGHT', PREFLIGHT_READY: 'READY', JOB_PAUSED: 'PAUSED', JOB_STOPPED: 'STOPPED',
  SHOT_SUBMITTED: 'SUBMITTING', RESULT_WAITING: 'WAITING_FOR_RESULT', SHOT_RESULT_FOUND: 'RESULT_IDENTIFIED',
  DOWNLOAD_STARTED: 'DOWNLOADING', VALIDATION_STARTED: 'VALIDATING', SHOT_ACCEPTED: 'ACCEPTED',
  SHOT_RETRY: 'RETRY_PENDING', DELAY_STARTED: 'DELAYING', SHOT_READY: 'READY', JOB_COMPLETED: 'COMPLETED',
  RENDER_STARTED: 'RENDERING',
};

function transition(state, event) {
  const current = typeof state === 'string' ? state : state.status;
  const type = typeof event === 'string' ? event : event?.type;
  const next = EVENT_STATE[type] ?? (event?.to);
  if (!LEGAL[current]) throw new Error(`Unknown state: ${current}`);
  if (!next || !LEGAL[current].includes(next)) throw new Error(`Illegal transition: ${current} -> ${next ?? type}`);
  if (typeof state === 'string') return next;
  return { ...state, status: next };
}

export { LEGAL, transition };
