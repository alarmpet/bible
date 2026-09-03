import { classifyFailure, randomDelayMs } from './retry-policy.js';

function createQueue(job, options = {}) {
  if (!job || !Array.isArray(job.shots)) throw new TypeError('job.shots must be an array');
  const retryLimit = options.retryLimit ?? job.retry_limit ?? 2;
  const shots = job.shots.map((shot) => ({ ...shot, status: shot.status ?? 'PENDING', attempt: shot.attempt ?? 0 }));
  let status = options.status ?? 'READY';
  let activeShotId = null;
  let stopped = false;
  const accepted = new Set(shots.filter((shot) => shot.status === 'ACCEPTED').map((shot) => shot.shot_id));
  const find = (id) => shots.find((shot) => shot.shot_id === id);
  function next() { if (stopped || status === 'PAUSED' || activeShotId) return null; return shots.find((shot) => !['ACCEPTED', 'COMPLETED', 'PAUSED'].includes(shot.status)) ?? null; }
  function snapshot() { return { job_id: job.job_id, status, active_shot_id: activeShotId, shots: shots.map((shot) => ({ ...shot })), accepted_shots: [...accepted] }; }
  function dispatch(event) {
    if (!event?.type) throw new TypeError('event.type is required');
    const shot = event.shot_id ? find(event.shot_id) : null;
    if (event.type === 'JOB_STOPPED') { stopped = true; status = 'STOPPED'; return snapshot(); }
    if (event.type === 'JOB_PAUSED') { status = 'PAUSED'; return snapshot(); }
    if (event.type === 'SHOT_RESULT_FOUND') { if (!shot) throw new Error('unknown shot'); if (activeShotId && activeShotId !== shot.shot_id) throw new Error('only one active shot is allowed'); activeShotId = shot.shot_id; shot.status = 'RESULT_IDENTIFIED'; return snapshot(); }
    if (event.type === 'SHOT_ACCEPTED') { if (!shot || !['RESULT_IDENTIFIED', 'VALIDATING'].includes(shot.status)) throw new Error('shot is not awaiting acceptance'); shot.status = 'ACCEPTED'; accepted.add(shot.shot_id); activeShotId = null; status = 'READY'; return snapshot(); }
    if (event.type === 'SHOT_SUBMITTED') { if (!shot || activeShotId) throw new Error('only one active shot is allowed'); activeShotId = shot.shot_id; shot.status = 'SUBMITTING'; shot.attempt += 1; status = 'SUBMITTING'; return snapshot(); }
    if (event.type === 'SHOT_RETRY') { if (!shot) throw new Error('unknown shot'); if (classifyFailure(event.code, shot.attempt, retryLimit) === 'pause') { shot.status = 'PAUSED'; status = 'PAUSED'; } else { shot.status = 'RETRY_PENDING'; status = 'RETRY_PENDING'; } activeShotId = null; return snapshot(); }
    const target = { DOWNLOAD_STARTED: 'DOWNLOADING', DOWNLOAD_COMPLETED: 'VALIDATING' }[event.type];
    if (target && shot) { shot.status = target; return snapshot(); }
    return snapshot();
  }
  return { dispatch, next, delayMs: (min = 5000, max = 15000) => randomDelayMs(min, max, options.randomValues), snapshot, stop: () => dispatch({ type: 'JOB_STOPPED' }) };
}
function selectNextShot(snapshot, mode = 'next') { if (!snapshot || !Array.isArray(snapshot.shots)) throw new TypeError('snapshot.shots must be an array'); if (mode === 'retry') return snapshot.shots.find((shot) => shot.status === 'RETRY_PENDING') ?? null; return snapshot.shots.find((shot) => !['ACCEPTED', 'COMPLETED', 'PAUSED'].includes(shot.status)) ?? null; }

export { createQueue, selectNextShot };
