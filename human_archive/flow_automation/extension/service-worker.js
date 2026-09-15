import { makeEnvelope } from './core/protocol.js';
import { DownloadRegistry } from './core/download-registry.js';

let nativePort;
let activeJobId;
let activeJob;
let activeJobState = {};
let isRunning = false;
let currentMode = 'missing';
let schedulingTimer = null;
let activeShotInProgress = false;

const downloadRegistry = new DownloadRegistry(chrome.storage?.local);

function broadcastToSidePanel(msg) {
  try {
    if (typeof chrome !== 'undefined' && chrome.runtime?.sendMessage) {
      chrome.runtime.sendMessage(msg).catch(() => {});
    }
  } catch (_) {}
}

chrome.runtime.onInstalled?.addListener?.(() => chrome.sidePanel?.setPanelBehavior?.({ openPanelOnActionClick: true }));
chrome.runtime.onStartup?.addListener?.(() => chrome.sidePanel?.setPanelBehavior?.({ openPanelOnActionClick: true }));

// Hydrate state from storage
if (typeof chrome !== 'undefined' && chrome.storage?.local) {
  chrome.storage.local.get(['activeJobId', 'activeJob', 'activeJobState', 'isRunning', 'currentMode'], (data) => {
    if (data?.activeJobId && data?.activeJob) {
      activeJobId = data.activeJobId;
      activeJob = data.activeJob;
      activeJobState = data.activeJobState || {};
      isRunning = Boolean(data.isRunning);
      currentMode = data.currentMode || 'missing';
      connectHost();
    }
  });
}

function connectHost() {
  if (!activeJobId || typeof chrome === 'undefined' || !chrome.runtime?.connectNative) return;
  if (nativePort) return;
  try {
    nativePort = chrome.runtime.connectNative('com.nollam.flow_automation');
    nativePort.onMessage.addListener(handleHostMessage);
    nativePort.onDisconnect.addListener(() => {
      nativePort = undefined;
      const err = chrome.runtime.lastError;
      if (err) console.warn('[NOLLAM] Native host disconnected:', err.message);
    });
    nativePort.postMessage(makeEnvelope('LOAD_JOB', activeJobId, { job: activeJob }));
  } catch (err) {
    console.error('[NOLLAM] connectHost error:', err);
  }
}

function handleHostMessage(message) {
  if (!message) return;
  chrome.runtime.sendMessage(message).catch(() => {});

  if (message.type === 'JOB_STATE') {
    activeJobState = message.payload || {};
    chrome.storage?.local?.set?.({ activeJobState });
    if (activeJobState.control_state === 'RUNNING') {
      isRunning = true;
      chrome.storage?.local?.set?.({ isRunning: true });
      if (!activeShotInProgress) scheduleNextShot(0);
    } else if (['PAUSED', 'STOPPED'].includes(activeJobState.control_state)) {
      isRunning = false;
      activeShotInProgress = false;
      if (schedulingTimer) clearTimeout(schedulingTimer);
      chrome.storage?.local?.set?.({ isRunning: false });
    }
  } else if (message.type === 'RUN_SHOT') {
    activeShotInProgress = true;
    const shotId = message.payload?.shot_id;
    const attempt = message.payload?.attempt || 1;
    const shot = activeJob?.shots?.find?.((s) => s.shot_id === shotId);
    if (!shot) {
      console.error('[NOLLAM] RUN_SHOT unknown shot:', shotId);
      activeShotInProgress = false;
      return;
    }
    // Broadcast to UI that shot is executing
    broadcastToSidePanel({
      type: 'SHOT_EXECUTING',
      payload: { shot_id: shotId, attempt }
    });

    // Query all tabs safely without match pattern syntax errors
    chrome.tabs.query({}, (tabs = []) => {
      const expectedUrl = activeJob?.project?.expected_url || 'https://labs.google/fx/ko/tools/flow/project/b0aa7ff4-49c0-4841-b333-7f4e52ddcc12';
      let tab = tabs.find((t) => t.url && (t.url.includes('flow/project') || t.url.includes('labs.google')));
      
      const dispatchToTab = (targetTabId) => {
        chrome.tabs.sendMessage(targetTabId, { type: 'EXECUTE_SHOT', job: activeJob, shot, attempt })
          .then((response) => {
            console.log('[NOLLAM] Shot dispatched successfully to tab:', targetTabId, response);
          })
          .catch((err) => {
            console.warn('[NOLLAM] Content script not responding, injecting content-script.js...', err.message);
            chrome.scripting.executeScript({
              target: { tabId: targetTabId },
              files: ['content/content-script.js']
            }).then(() => {
              setTimeout(() => {
                chrome.tabs.sendMessage(targetTabId, { type: 'EXECUTE_SHOT', job: activeJob, shot, attempt })
                  .then((res) => console.log('[NOLLAM] Dispatched after injection:', res))
                  .catch((e) => console.error('[NOLLAM] Retry failed:', e));
              }, 1200);
            }).catch((scriptErr) => {
              console.error('[NOLLAM] Script injection failed:', scriptErr);
              activeShotInProgress = false;
            });
          });
      };

      if (tab?.id) {
        dispatchToTab(tab.id);
      } else {
        chrome.tabs.create({ url: expectedUrl }, (newTab) => {
          setTimeout(() => {
            if (newTab?.id) dispatchToTab(newTab.id);
          }, 4000);
        });
      }
    });
  } else if (message.type === 'SHOT_ACCEPTED') {
    activeShotInProgress = false;
    const minDelay = activeJob?.random_delay_seconds?.min || 5;
    const maxDelay = activeJob?.random_delay_seconds?.max || 15;
    const delay = Math.floor(Math.random() * (maxDelay - minDelay + 1) + minDelay) * 1000;
    scheduleNextShot(delay);
  } else if (message.type === 'SHOT_RETRY') {
    activeShotInProgress = false;
    scheduleNextShot(5000);
  } else if (message.type === 'JOB_PAUSED') {
    isRunning = false;
    activeShotInProgress = false;
    chrome.storage?.local?.set?.({ isRunning: false });
  }
}

function scheduleNextShot(delayMs = 0) {
  if (schedulingTimer) clearTimeout(schedulingTimer);
  if (!isRunning || !activeJob || !nativePort) return;

  schedulingTimer = setTimeout(() => {
    if (!isRunning || activeShotInProgress) return;
    const shotsState = activeJobState?.shots || {};
    const candidate = activeJob.shots?.find?.((shot) => {
      const s = shotsState[shot.shot_id];
      const status = s?.status || 'PENDING';
      if (['ACCEPTED', 'COMPLETED', 'EXHAUSTED'].includes(status)) return false;
      return true;
    });

    if (!candidate) {
      isRunning = false;
      chrome.storage?.local?.set?.({ isRunning: false });
      nativePort?.postMessage?.(makeEnvelope('JOB_COMPLETED', activeJobId, {}));
      return;
    }

    activeShotInProgress = true;
    nativePort?.postMessage?.(makeEnvelope('SHOT_SUBMITTED', activeJobId, {
      shot_id: candidate.shot_id,
      attempt: (shotsState[candidate.shot_id]?.attempt || 0) + 1
    }));
  }, delayMs);
}

chrome.runtime.onStartup?.addListener?.(connectHost);
chrome.runtime.onInstalled?.addListener?.(connectHost);

chrome.runtime.onMessage?.addListener?.((message, sender, sendResponse) => {
  if (!message) return false;

  if (message.type === 'SET_ACTIVE_JOB') {
    activeJobId = String(message.job_id || '');
    activeJob = message.job;
    isRunning = false;
    activeShotInProgress = false;
    chrome.storage?.local?.set?.({ activeJobId, activeJob, isRunning: false });
    connectHost();
    sendResponse({ ok: Boolean(activeJobId && activeJob) });
    return true;
  }

  if (message.type === 'JOB_START_REQUESTED') {
    isRunning = true;
    currentMode = message.payload?.mode || 'missing';
    chrome.storage?.local?.set?.({ isRunning: true, currentMode });
    if (!nativePort) connectHost();
    if (nativePort) {
      nativePort.postMessage(makeEnvelope('JOB_START_REQUESTED', activeJobId, message.payload || {}));
    }
    sendResponse({ ok: true });
    return true;
  }

  if (message.type === 'JOB_STOPPED') {
    isRunning = false;
    activeShotInProgress = false;
    if (schedulingTimer) clearTimeout(schedulingTimer);
    chrome.storage?.local?.set?.({ isRunning: false });
    if (nativePort) {
      nativePort.postMessage(makeEnvelope('JOB_STOPPED', activeJobId, {}));
    }
    sendResponse({ ok: true });
    return true;
  }

  if (message.type === 'CONTENT_SHOT_COMPLETED') {
    const { shot, cardId, mediaIdentity, mediaUrl, attempt = 1 } = message;
    if (typeof chrome !== 'undefined' && chrome.downloads?.download && mediaUrl) {
      chrome.downloads.download({
        url: mediaUrl,
        filename: shot.expected_filename,
        saveAs: false
      }, (downloadId) => {
        if (downloadId !== undefined) {
          downloadRegistry.register(downloadId, {
            jobId: activeJobId,
            shotId: shot.shot_id,
            promptSha256: shot.prompt_sha256,
            attempt,
            cardId: cardId || `card-${shot.shot_id}`,
            mediaIdentity: mediaIdentity || `media-${shot.shot_id}`
          });
          if (nativePort) {
            nativePort.postMessage(makeEnvelope('DOWNLOAD_STARTED', activeJobId, {
              shot_id: shot.shot_id,
              attempt,
              download_id: String(downloadId)
            }));
          }
        }
      });
    }
    sendResponse({ ok: true });
    return true;
  }

  if (message.type === 'CONTENT_SHOT_ERROR') {
    activeShotInProgress = false;
    if (nativePort) {
      nativePort.postMessage(makeEnvelope('JOB_PAUSED', activeJobId, {
        shot_id: message.shot_id,
        code: message.code || 'SHOT_EXECUTION_ERROR'
      }));
    }
    sendResponse({ ok: true });
    return true;
  }

  if (!nativePort) connectHost();
  if (nativePort) {
    const outgoing = message.protocol_version === 1 ? message : makeEnvelope(message.type, activeJobId, message.payload || {});
    nativePort.postMessage(outgoing);
  }
  sendResponse({ ok: Boolean(nativePort) });
  return true;
});

chrome.downloads?.onChanged?.addListener?.((delta) => {
  if (delta.state?.current !== 'complete') return;
  chrome.downloads.search({ id: delta.id }).then(([item]) => {
    const result = downloadRegistry.complete(delta.id, item?.filename || '');
    if (nativePort && result.status === 'complete') {
      nativePort.postMessage(makeEnvelope('DOWNLOAD_COMPLETED', result.jobId, result));
    }
  }).catch(() => {});
});

