import { SELECTORS_V1 } from './selectors.js';

const first = (root, selector) => root?.querySelector?.(selector) ?? null;
const all = (root, selector) => [...(root?.querySelectorAll?.(selector) ?? [])];

function captureBaseline(document) {
  return { cardIds: all(document, SELECTORS_V1.resultCard).map((card) => String(card.dataset?.cardId || card.id || '')).filter(Boolean) };
}

function identifyCompletedCard(document, baseline = { cardIds: [] }) {
  const cards = all(document, SELECTORS_V1.resultCard);
  if (!cards.length) return { status: 'error', code: 'FLOW_UI_CHANGED' };
  if (first(document, SELECTORS_V1.busy)) return { status: 'pending', code: 'GENERATING' };
  const known = new Set(baseline.cardIds || []);
  const candidates = cards.filter((card) => {
    const id = String(card.dataset?.cardId || card.id || '');
    const media = first(card, SELECTORS_V1.media);
    return id && !known.has(id) && media && Number(media.naturalWidth || media.width) > 0 && Number(media.naturalHeight || media.height) > 0 && Number(card.dataset?.stableObservations || 2) >= 2;
  });
  if (candidates.length !== 1) return { status: 'error', code: candidates.length ? 'AMBIGUOUS_RESULT' : 'RESULT_NOT_READY' };
  const card = candidates[0];
  const media = first(card, SELECTORS_V1.media);
  return { status: 'complete', cardId: String(card.dataset.cardId || card.id), mediaIdentity: String(card.dataset.mediaIdentity || media.dataset?.mediaIdentity || ''), width: Number(media.naturalWidth || media.width), height: Number(media.naturalHeight || media.height) };
}

function preflight(document, location, job) {
  const url = String(location?.href || location || '');
  if (url !== String(job?.project?.expected_url || '')) return { ok: false, code: 'PROJECT_MISMATCH' };
  if (String(job?.media_type || 'image') !== 'image') return { ok: false, code: 'MODE_MISMATCH' };
  if (!first(document, SELECTORS_V1.promptEditor) || !all(document, SELECTORS_V1.resultCard).length) return { ok: false, code: 'FLOW_UI_CHANGED' };
  if (first(document, '[role="dialog"][data-blocking="true"]')) return { ok: false, code: 'FLOW_BLOCKED' };
  return { ok: true };
}

function submitPrompt(document, prompt) {
  const editor = first(document, SELECTORS_V1.promptEditor);
  if (!editor) return { ok: false, code: 'FLOW_UI_CHANGED' };
  editor.textContent = String(prompt);
  editor.dispatchEvent?.(new Event('input', { bubbles: true }));
  return { ok: true, prompt: String(prompt) };
}

export { captureBaseline, identifyCompletedCard, preflight, submitPrompt };
