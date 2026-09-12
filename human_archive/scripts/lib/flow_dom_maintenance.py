"""Shared Flow canvas error recovery and verified-card garbage collection.

The three Flow entrypoints use the same browser surface.  Keeping the DOM
selectors and recovery order here prevents one pipeline from silently drifting
to a different retry or cleanup policy.
"""

from __future__ import annotations

import time
import re
from typing import Any


DOM_GC_BATCH_SIZE = 25


def dom_gc_due(verified_count: int, *, batch_size: int = DOM_GC_BATCH_SIZE) -> bool:
    """Return whether a verified-card GC commit is due.

    GC is only safe after local download verification.  A zero/negative count
    or an invalid batch size must never trigger a browser mutation.
    """
    return batch_size > 0 and verified_count > 0 and verified_count % batch_size == 0


def error_recovery_action(attempt: int) -> str:
    """Return the bounded action for an error card recovery attempt."""
    if attempt <= 1:
        return "retry"
    if attempt == 2:
        return "trash"
    return "fail"


async def wait_for_canvas_idle(
    page: Any, *, timeout_sec: float = 90.0, poll_ms: int = 2_000
) -> bool:
    """Wait until Flow reports no progress percentage and no active spinner."""
    started = time.monotonic()
    while time.monotonic() - started < timeout_sec:
        try:
            state = await page.evaluate(r"""
() => {
    const bodyText = document.body?.innerText || '';
    const spinners = document.querySelectorAll(
        'mat-progress-spinner, [role="progressbar"], flow-progress'
    );
    return {bodyText, spinnerCount: spinners.length};
}
""") or {}
            body = str(state.get("bodyText", ""))
            spinner_count = int(state.get("spinnerCount", 0))
            if not re.search(r"\b\d{1,2}%", body) and spinner_count == 0:
                return True
        except Exception:
            pass
        await page.wait_for_timeout(max(1, poll_ms))
    return False


_CLEAR_ERROR_CARDS_JS = r"""
() => {
    let cleared = 0;
    const errorTiles = document.querySelectorAll(
        'flow-error-tile, .error-tile, .error-tile-content, [role="alert"], div[class*="error"], div[class*="Error"]'
    );
    for (const tile of errorTiles) {
        const text = (tile.innerText || '').trim();
        const looksLikeError = text.includes('오류') || text.includes('실패') ||
            text.includes('로드할 수 없습니다') || text.includes('안전') ||
            text.includes('정책') || text.includes('활동') || text.includes('감지') ||
            text.toLowerCase().includes('error') || text.toLowerCase().includes('failed') ||
            text.toLowerCase().includes('violation') || text.toLowerCase().includes('blocked') ||
            text.toLowerCase().includes('unusual');
        if (!looksLikeError) continue;

        const buttons = Array.from(tile.querySelectorAll('button'));
        const trash = buttons.find((button) => {
            const label = ((button.getAttribute('aria-label') || '') + ' ' +
                (button.innerText || '')).toLowerCase();
            return label.includes('삭제') || label.includes('휴지통') ||
                label.includes('delete') || label.includes('delete_forever');
        });
        const retry = buttons.find((button) => {
            const label = ((button.getAttribute('aria-label') || '') + ' ' +
                (button.innerText || '')).toLowerCase();
            return label.includes('다시 시도') || label.includes('retry') ||
                label.includes('refresh') || label.includes('redo');
        });
        const providerBlock = text.includes('활동') || text.includes('감지') ||
            text.includes('정책') || text.includes('안전') ||
            text.toLowerCase().includes('blocked') || text.toLowerCase().includes('unusual');
        const target = trash || (providerBlock ? null : retry);
        target?.click();
        if (target) cleared++;
    }
    return cleared;
}
"""


_GC_VERIFIED_CARDS_JS = r"""
(maxCount) => {
    const cards = Array.from(document.querySelectorAll(
        '[data-card-id], .generation-card, div[class*="media-card"]'
    ));
    let trashed = 0;
    for (const card of cards.slice(0, Math.max(0, maxCount))) {
        const buttons = Array.from(card.querySelectorAll('button'))
            .concat(card.parentElement ? Array.from(card.parentElement.querySelectorAll('button')) : []);
        const trash = buttons.find((button) => {
            const label = ((button.getAttribute('aria-label') || '') + ' ' +
                (button.innerText || '')).toLowerCase();
            return label.includes('삭제') || label.includes('휴지통') || label.includes('delete');
        });
        if (trash) {
            trash.click();
            trashed++;
        }
    }
    return trashed;
}
"""


async def clear_error_cards(page: Any) -> int:
    """Retry or trash visible Flow error cards and return the action count."""
    try:
        return int(await page.evaluate(_CLEAR_ERROR_CARDS_JS) or 0)
    except Exception:
        return 0


async def clear_first_error_card(page: Any) -> str | None:
    """Return a short error description after applying shared recovery."""
    try:
        result = await page.evaluate(r"""
() => {
    const cards = Array.from(document.querySelectorAll(
        'flow-error-tile, .error-tile, .error-tile-content, [role="alert"], div[class*="error"], div[class*="Error"]'
    ));
    for (const card of cards) {
        const text = (card.innerText || '').trim();
        if (!text) continue;
        const lower = text.toLowerCase();
        const looksLikeError = text.includes('오류') || text.includes('실패') ||
            text.includes('안전') || text.includes('정책') || text.includes('활동') ||
            text.includes('감지') || lower.includes('error') || lower.includes('failed') ||
            lower.includes('violation') || lower.includes('blocked') || lower.includes('unusual');
        if (!looksLikeError) continue;
        const buttons = Array.from(card.querySelectorAll('button'));
        const trash = buttons.find((candidate) => {
            const label = ((candidate.getAttribute('aria-label') || '') + ' ' +
                (candidate.innerText || '')).toLowerCase();
            return label.includes('삭제') || label.includes('휴지통') ||
                label.includes('delete') || label.includes('delete_forever');
        });
        const retry = buttons.find((candidate) => {
            const label = ((candidate.getAttribute('aria-label') || '') + ' ' +
                (candidate.innerText || '')).toLowerCase();
            return label.includes('다시 시도') || label.includes('retry') ||
                label.includes('refresh') || label.includes('redo');
        });
        const providerBlock = text.includes('활동') || text.includes('감지') ||
            text.includes('정책') || text.includes('안전') ||
            lower.includes('blocked') || lower.includes('unusual');
        const button = trash || (providerBlock ? null : retry);
        if (button) button.click();
        return {text: text.slice(0, 100), acted: Boolean(button)};
    }
    return null;
}
""")
        if result:
            return str(result.get("text", "Flow error card detected"))
    except Exception:
        pass
    return None


async def cleanup_verified_cards(page: Any, max_count: int = DOM_GC_BATCH_SIZE) -> int:
    """Trash at most ``max_count`` cards after their files were verified."""
    if max_count <= 0:
        return 0
    try:
        return int(await page.evaluate(_GC_VERIFIED_CARDS_JS, max_count) or 0)
    except Exception:
        return 0
