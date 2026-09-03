function renderModel(snapshot = {}) {
  const blockers = [];
  if (snapshot.projectMatch === false) blockers.push('PROJECT_MISMATCH');
  if (snapshot.mediaMode && snapshot.mediaMode !== 'image') blockers.push('MEDIA_TYPE_MISMATCH');
  if (snapshot.blockers) for (const code of snapshot.blockers) if (!blockers.includes(code)) blockers.push(code);
  const state = snapshot.state || snapshot.control_state || 'IDLE';
  return { canStart: blockers.length === 0 && !['WAITING_FOR_RESULT', 'SUBMITTING', 'PAUSED'].includes(state), canStop: !['IDLE', 'COMPLETED', 'STOPPED'].includes(state), blockers, state, shots: snapshot.shots || [], passed: snapshot.passed || 0, total: snapshot.total || (snapshot.shots || []).length };
}

const port = typeof chrome !== 'undefined' ? chrome.runtime.connect() : null;
function send(type, payload = {}) { port?.postMessage({ type, ...payload }); }
if (typeof document !== 'undefined') {
  document.querySelector('#generate-missing')?.addEventListener('click', () => send('JOB_START_REQUESTED', { mode: 'missing', retry_limit: 2, max_attempts: 3 }));
  document.querySelector('#generate-all')?.addEventListener('click', () => send('JOB_START_REQUESTED', { mode: 'all', retry_limit: 2, max_attempts: 3 }));
  document.querySelector('#stop')?.addEventListener('click', () => send('JOB_STOPPED'));
}
export { renderModel };
