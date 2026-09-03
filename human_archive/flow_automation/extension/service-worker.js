import { makeEnvelope } from './core/protocol.js';
import { DownloadRegistry } from './core/download-registry.js';

let nativePort;
let activeJobId;
const downloadRegistry = new DownloadRegistry(chrome.storage?.local);
chrome.runtime.onInstalled.addListener(() => chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true }));
chrome.runtime.onStartup.addListener(() => chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true }));

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
chrome.downloads?.onChanged?.addListener((delta) => {
  if (delta.state?.current !== 'complete') return;
  chrome.downloads.search({ id: delta.id }).then(([item]) => {
    const result = downloadRegistry.complete(delta.id, item?.filename || '');
    if (nativePort && result.status === 'complete') nativePort.postMessage(makeEnvelope('DOWNLOAD_COMPLETED', result.jobId, result));
  }).catch(() => {});
});
