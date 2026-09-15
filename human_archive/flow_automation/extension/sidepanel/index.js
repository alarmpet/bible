function renderModel(snapshot = {}) {
  const blockers = [];
  if (snapshot.projectMatch === false) blockers.push('PROJECT_MISMATCH');
  if (snapshot.mediaMode && snapshot.mediaMode !== 'image') blockers.push('MEDIA_TYPE_MISMATCH');
  for (const code of snapshot.blockers || []) if (!blockers.includes(code)) blockers.push(code);
  const state = snapshot.state || snapshot.control_state || 'IDLE';
  return { canStart: blockers.length === 0 && !['WAITING_FOR_RESULT', 'SUBMITTING', 'PAUSED'].includes(state), canStop: !['IDLE', 'COMPLETED', 'STOPPED'].includes(state), blockers, state, shots: snapshot.shots || [], passed: snapshot.passed || 0, total: snapshot.total || (snapshot.shots || []).length };
}

let activeJob;
let latestSnapshot = {};

function logStatus(msg, isError = false) {
  if (typeof document === 'undefined') return;
  const box = document.querySelector('#status-box');
  if (box) {
    box.textContent = msg;
    box.style.color = isError ? '#ef4444' : '#38bdf8';
  }
}

function renderTable(shots = [], shotsState = {}) {
  if (typeof document === 'undefined') return;
  const tbody = document.querySelector('#shots tbody');
  if (!tbody) return;
  tbody.innerHTML = '';
  for (const s of shots) {
    const id = typeof s === 'string' ? s : s.shot_id;
    const st = shotsState[id] || {};
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><b>${id}</b></td>
      <td><span style="padding:2px 6px;border-radius:3px;background:#334155;color:#f8fafc;font-size:11px;">${st.status || 'PENDING'}</span></td>
      <td>${st.attempt || 0}</td>
      <td style="color:${st.approved_path ? '#10b981' : '#94a3b8'}">${st.approved_path ? 'APPROVED' : '-'}</td>
      <td style="color:#ef4444;font-size:11px;">${st.error || '-'}</td>
    `;
    tbody.appendChild(tr);
  }
}

function send(type, payload = {}) {
  if (typeof chrome === 'undefined') return;
  const jobId = activeJob?.job_id || latestSnapshot?.job_id || 'active-job';
  logStatus(`Sending ${type}...`);
  chrome.runtime.sendMessage({ type, job_id: jobId, payload }, (resp) => {
    if (chrome.runtime.lastError) {
      logStatus(`Send error: ${chrome.runtime.lastError.message}`, true);
    } else {
      logStatus(`Command ${type} accepted.`);
    }
  });
}

function update(snapshot = {}) {
  latestSnapshot = snapshot;
  if (typeof document === 'undefined') return;
  const model = renderModel({ ...snapshot, projectMatch: true, mediaMode: activeJob?.media_type || 'image' });
  
  const gm = document.querySelector('#generate-missing');
  if (gm) gm.disabled = !activeJob ? true : (!model.canStart && !['IDLE', 'READY', 'RUNNING'].includes(model.state));
  
  const ga = document.querySelector('#generate-all');
  if (ga) ga.disabled = !activeJob ? true : (!model.canStart && !['IDLE', 'READY', 'RUNNING'].includes(model.state));
  
  const st = document.querySelector('#stop');
  if (st) st.disabled = !model.canStop;
  
  const res = document.querySelector('#resume');
  if (res) res.disabled = !activeJob;
  
  const ac = document.querySelector('#approve-contact-sheet');
  if (ac) ac.disabled = !activeJob;

  if (activeJob?.shots) {
    renderTable(activeJob.shots, snapshot.shots || {});
  }
}

if (typeof document !== 'undefined') {
  document.querySelector('#generate-missing')?.addEventListener('click', () => {
    logStatus('Starting Generate Missing...');
    send('JOB_START_REQUESTED', { mode: 'missing', retry_limit: 2, max_attempts: 3 });
  });

  document.querySelector('#generate-all')?.addEventListener('click', () => {
    logStatus('Starting Generate All...');
    send('JOB_START_REQUESTED', { mode: 'all', retry_limit: 2, max_attempts: 3 });
  });

  document.querySelector('#stop')?.addEventListener('click', () => {
    logStatus('Stopping Job...');
    send('JOB_STOPPED');
  });

  document.querySelector('#resume')?.addEventListener('click', () => {
    logStatus('Resuming Job...');
    send('JOB_START_REQUESTED', { mode: 'missing', retry_limit: 2, max_attempts: 3 });
  });

  document.querySelector('#approve-contact-sheet')?.addEventListener('click', () => {
    send('SEMANTIC_REVIEW_APPROVED');
  });

  document.querySelector('#job-file')?.addEventListener('change', async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      const job = JSON.parse(await file.text());
      if (!job.job_id || !job.project?.expected_url || !Array.isArray(job.shots)) {
        throw new Error('invalid job schema');
      }
      activeJob = job;
      window.__activeJob = job;
      document.querySelector('#scope').textContent = `${job.job_id} | ${job.shots.length} shots`;
      logStatus(`Job loaded: ${job.shots.length} shots. Ready to generate.`);
      renderTable(job.shots, {});
      update({ state: 'READY', shots: job.shots, total: job.shots.length });
      chrome.runtime.sendMessage({ type: 'SET_ACTIVE_JOB', job_id: job.job_id, job }).catch(() => {});
    } catch (error) {
      document.querySelector('#scope').textContent = 'Job load failed: ' + error.message;
      logStatus('Load error: ' + error.message, true);
    }
  });
}

if (typeof chrome !== 'undefined') {
  chrome.runtime.onMessage?.addListener((message) => {
    if (!message) return;
    if (message.type === 'JOB_STATE') {
      logStatus(`State: ${message.payload?.control_state || 'ACTIVE'}`);
      update(message.payload);
    } else if (message.type === 'JOB_PAUSED') {
      logStatus(`Paused: ${message.payload?.code || 'PAUSED'}`, true);
      update({ control_state: 'PAUSED', blockers: [message.payload?.code || 'PAUSED'] });
    } else if (message.type === 'SHOT_EXECUTING') {
      logStatus(`Dispatching ${message.payload?.shot_id} to Flow...`);
    } else if (message.type === 'SHOT_GENERATING') {
      logStatus(`Generating ${message.shot_id}... Waiting for result.`);
    } else if (message.type === 'SHOT_ACCEPTED') {
      logStatus(`Shot Accepted: ${message.payload?.shot_id}`);
    } else if (message.type === 'JOB_COMPLETED') {
      logStatus('All shots completed successfully!');
    }
  });
}

export { renderModel };

