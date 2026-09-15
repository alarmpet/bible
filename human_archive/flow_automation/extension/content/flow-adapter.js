export { captureBaseline, identifyCompletedCard, preflight, submitPrompt } from './completion-detector.js';

import { captureBaseline, identifyCompletedCard, preflight, submitPrompt } from './completion-detector.js';

if (typeof window !== 'undefined' && typeof chrome !== 'undefined' && chrome.runtime?.onMessage) {
  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (!message || !message.type) return false;

    if (message.type === 'PING') {
      sendResponse({ ok: true, url: window.location.href });
      return true;
    }

    if (message.type === 'PREFLIGHT') {
      const result = preflight(document, window.location, message.job);
      sendResponse(result);
      return true;
    }

    if (message.type === 'EXECUTE_SHOT') {
      (async () => {
        const { job, shot, attempt = 1 } = message;
        const pre = preflight(document, window.location, job);
        if (!pre.ok) {
          chrome.runtime.sendMessage({
            type: 'CONTENT_SHOT_ERROR',
            job_id: job.job_id,
            shot_id: shot.shot_id,
            attempt,
            code: pre.code
          }).catch(() => {});
          return;
        }

        const baseline = captureBaseline(document);
        let sub = submitPrompt(document, shot.prompt);
        if (!sub.ok) {
          for (let i = 0; i < 10; i++) {
            await new Promise((r) => setTimeout(r, 1000));
            sub = submitPrompt(document, shot.prompt);
            if (sub.ok) break;
          }
        }
        if (!sub.ok) {
          chrome.runtime.sendMessage({
            type: 'CONTENT_SHOT_ERROR',
            job_id: job.job_id,
            shot_id: shot.shot_id,
            attempt,
            code: sub.code
          }).catch(() => {});
          return;
        }

        const startTime = Date.now();
        const timeoutMs = 120000;
        const pollIntervalMs = 1000;

        const checkCard = () => {
          if (Date.now() - startTime > timeoutMs) {
            chrome.runtime.sendMessage({
              type: 'CONTENT_SHOT_ERROR',
              job_id: job.job_id,
              shot_id: shot.shot_id,
              attempt,
              code: 'TIMEOUT'
            }).catch(() => {});
            return;
          }

          const status = identifyCompletedCard(document, baseline);
          if (status.status === 'pending') {
            setTimeout(checkCard, pollIntervalMs);
            return;
          }

          if (status.status === 'error') {
            chrome.runtime.sendMessage({
              type: 'CONTENT_SHOT_ERROR',
              job_id: job.job_id,
              shot_id: shot.shot_id,
              attempt,
              code: status.code
            }).catch(() => {});
            return;
          }

          if (status.status === 'complete') {
            const cardElem = document.querySelector(`[data-card-id="${status.cardId}"], #${status.cardId}`);
            const img = cardElem?.querySelector?.('img[src],picture img[src]');
            const mediaUrl = img?.src || '';

            chrome.runtime.sendMessage({
              type: 'CONTENT_SHOT_COMPLETED',
              job_id: job.job_id,
              shot_id: shot.shot_id,
              attempt,
              cardId: status.cardId,
              mediaIdentity: status.mediaIdentity,
              mediaUrl,
              shot
            }).catch(() => {});
          }
        };

        setTimeout(checkCard, 2000);
      })();

      sendResponse({ ok: true });
      return true;
    }
  });
}
