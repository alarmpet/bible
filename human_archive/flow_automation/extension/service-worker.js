import { makeEnvelope } from './core/protocol.js';

let nativePort;
let activeJobId;

function connectHost() {
  if (!activeJobId) return;
  nativePort = chrome.runtime.connectNative('com.nollam.flow_automation');
  nativePort.onMessage.addListener((message) => chrome.runtime.sendMessage(message));
  nativePort.onDisconnect.addListener(() => { nativePort = undefined; });
  nativePort.postMessage(makeEnvelope('LOAD_JOB', activeJobId, {}));
}

chrome.runtime.onStartup.addListener(connectHost);
chrome.runtime.onInstalled.addListener(connectHost);
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.type === 'SET_ACTIVE_JOB') { activeJobId = String(message.job_id || ''); connectHost(); sendResponse({ ok: true }); return true; }
  if (!nativePort) connectHost();
  if (nativePort) nativePort.postMessage(message);
  sendResponse({ ok: Boolean(nativePort) });
  return true;
});
