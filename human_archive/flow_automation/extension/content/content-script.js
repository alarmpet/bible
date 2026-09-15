// Self-contained classic content script for Google Flow automation
(() => {
  if (window.__nollam_content_script_loaded) {
    console.log('[NOLLAM] Content script already active.');
    return;
  }
  window.__nollam_content_script_loaded = true;
  console.log('[NOLLAM] Flow Automation Content Script initialized.');

  const SELECTORS = {
    promptEditor: "div[role='textbox'], [data-slate-editor='true'], textarea",
    resultCard: "[data-testid='generation-card'], [data-card-id]",
    media: "img[src], picture img[src]",
    busy: "[aria-busy='true'], [role='progressbar']"
  };

 const first = (root, selector) => root?.querySelector?.(selector) ?? null;
 const all = (root, selector) => [...(root?.querySelectorAll?.(selector) ?? [])];

 function captureBaseline() {
 return all(document, SELECTORS.resultCard)
 .map((c) => c.getAttribute('data-card-id') || c.id || c.getAttribute('data-testid') || '')
 .filter(Boolean);
 }

 async function submitPrompt(promptText) {
 let editor = null;
 for (let i = 0; i < 15; i++) {
 editor = first(document, SELECTORS.promptEditor);
 if (editor && editor.offsetParent !== null) break;
 await new Promise((r) => setTimeout(r, 1000));
 }

 if (!editor) {
 return { ok: false, code: 'FLOW_UI_CHANGED' };
 }

 try {
 editor.focus();
 if (editor.isContentEditable) {
 editor.textContent = '';
 document.execCommand('insertText', false, promptText);
 editor.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: promptText }));
 } else {
 editor.value = promptText;
 editor.dispatchEvent(new Event('input', { bubbles: true }));
 editor.dispatchEvent(new Event('change', { bubbles: true }));
 }

      await new Promise((r) => setTimeout(r, 400));

      // 1. Dispatch Enter key events
      const enterDown = new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true, cancelable: true });
      const enterPress = new KeyboardEvent('keypress', { key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true, cancelable: true });
      const enterUp = new KeyboardEvent('keyup', { key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true, cancelable: true });
      editor.dispatchEvent(enterDown);
      editor.dispatchEvent(enterPress);
      editor.dispatchEvent(enterUp);

      await new Promise((r) => setTimeout(r, 500));

      // 2. Find and click the submit / arrow button in the editor toolbar
      const buttons = all(document, 'button');
      let submitBtn = null;
      
      // Look for arrow or submit button
      for (const btn of buttons) {
        const label = (btn.getAttribute('aria-label') || '').toLowerCase();
        const text = (btn.innerText || '').toLowerCase();
        if (label.includes('생성') || label.includes('만들기') || label.includes('전송') || label.includes('submit') || label.includes('generate') || label.includes('send')) {
          submitBtn = btn;
          break;
        }
      }

      // If not found by label, look for button with arrow SVG near the editor
      if (!submitBtn) {
        const editorRect = editor.getBoundingClientRect();
        for (const btn of buttons) {
          const rect = btn.getBoundingClientRect();
          if (rect.bottom >= editorRect.top && rect.top <= editorRect.bottom + 100 && rect.right > editorRect.left) {
            const hasSvg = btn.querySelector('svg');
            if (hasSvg && !btn.disabled) {
              submitBtn = btn; // The arrow button is on the right of the bottom toolbar
            }
          }
        }
      }

      if (submitBtn) {
        console.log('[NOLLAM] Triggering submit button click:', submitBtn);
        submitBtn.focus();
        submitBtn.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
        submitBtn.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
        submitBtn.click();
      } else {
        console.log('[NOLLAM] No explicit submit button found, relied on Enter key.');
      }

      return { ok: true };
    } catch (err) {
      return { ok: false, code: 'SUBMIT_EXCEPTION', message: err.message };
    }
 }

 chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
 if (!message || !message.type) return false;

 if (message.type === 'PING') {
 sendResponse({ ok: true, url: window.location.href });
 return true;
 }

 if (message.type === 'EXECUTE_SHOT') {
 sendResponse({ received: true });

 const { job, shot, attempt = 1 } = message;
 console.log('[NOLLAM] Received EXECUTE_SHOT:', shot.shot_id, 'attempt:', attempt);

 (async () => {
 const baselineIds = captureBaseline();
 console.log('[NOLLAM] Captured baseline count:', baselineIds.length);

 const sub = await submitPrompt(shot.prompt);
 if (!sub.ok) {
 console.error('[NOLLAM] Failed to submit prompt:', sub.code);
 chrome.runtime.sendMessage({
 type: 'CONTENT_SHOT_ERROR',
 job_id: job.job_id,
 shot_id: shot.shot_id,
 attempt,
 code: sub.code
 }).catch(() => {});
 return;
 }

 console.log('[NOLLAM] Prompt submitted for', shot.shot_id, ', polling for new card...');
 chrome.runtime.sendMessage({
   type: 'SHOT_GENERATING',
   job_id: job.job_id,
   shot_id: shot.shot_id
 }).catch(() => {});

 const startTime = Date.now();
 const timeoutMs = 120000;
 const baselineSet = new Set(baselineIds);

 const pollTimer = setInterval(() => {
 if (Date.now() - startTime > timeoutMs) {
 clearInterval(pollTimer);
 console.error('[NOLLAM] Timeout waiting for card', shot.shot_id);
 chrome.runtime.sendMessage({
 type: 'CONTENT_SHOT_ERROR',
 job_id: job.job_id,
 shot_id: shot.shot_id,
 attempt,
 code: 'TIMEOUT'
 }).catch(() => {});
 return;
 }

 const currentCards = all(document, SELECTORS.resultCard);
 const newCandidates = [];

 for (const card of currentCards) {
 const cid = card.getAttribute('data-card-id') || card.id || card.getAttribute('data-testid');
 if (cid && !baselineSet.has(cid)) {
 const media = first(card, SELECTORS.media);
 if (media && (media.naturalWidth > 0 || media.width > 0) && media.src && !media.src.startsWith('data:')) {
 newCandidates.push({
 cardId: cid,
 src: media.src,
 width: media.naturalWidth || media.width,
 height: media.naturalHeight || media.height
 });
 }
 }
 }

 if (newCandidates.length === 1) {
 clearInterval(pollTimer);
 const chosen = newCandidates[0];
 console.log('[NOLLAM] Successfully identified completed card:', chosen.cardId);

 chrome.runtime.sendMessage({
 type: 'CONTENT_SHOT_COMPLETED',
 job_id: job.job_id,
 shot_id: shot.shot_id,
 attempt,
 card_id: chosen.cardId,
 media_url: chosen.src,
 width: chosen.width,
 height: chosen.height
 }).catch((e) => console.error('[NOLLAM] Error sending completion:', e));
 } else if (newCandidates.length > 1) {
 clearInterval(pollTimer);
 console.warn('[NOLLAM] Ambiguous cards detected:', newCandidates.length);
 chrome.runtime.sendMessage({
 type: 'CONTENT_SHOT_ERROR',
 job_id: job.job_id,
 shot_id: shot.shot_id,
 attempt,
 code: 'AMBIGUOUS_RESULT'
 }).catch(() => {});
 }
 }, 1000);
 })();

 return true;
 }
 });
})();
