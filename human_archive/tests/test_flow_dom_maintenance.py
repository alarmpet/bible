from __future__ import annotations

import asyncio

from lib.flow_dom_maintenance import (
    DOM_GC_BATCH_SIZE,
    clear_error_cards,
    cleanup_verified_cards,
    dom_gc_due,
    error_recovery_action,
    wait_for_canvas_idle,
)


def test_gc_policy_is_25_verified_cards_and_never_zero() -> None:
    assert DOM_GC_BATCH_SIZE == 25
    assert not dom_gc_due(0)
    assert not dom_gc_due(24)
    assert dom_gc_due(25)
    assert dom_gc_due(50)


def test_error_recovery_is_bounded_and_ordered() -> None:
    assert error_recovery_action(1) == "retry"
    assert error_recovery_action(2) == "trash"
    assert error_recovery_action(3) == "fail"


class _FakePage:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object | None]] = []

    async def evaluate(self, script: str, argument: object | None = None):
        self.calls.append((script, argument))
        return 2


def test_shared_browser_helpers_use_the_same_js_contract() -> None:
    page = _FakePage()
    assert asyncio.run(clear_error_cards(page)) == 2
    assert asyncio.run(cleanup_verified_cards(page, 25)) == 2
    assert len(page.calls) == 2
    assert "flow-error-tile" in page.calls[0][0]
    assert "media-card" in page.calls[1][0]
    assert page.calls[1][1] == 25


class _IdlePage:
    async def evaluate(self, script: str):
        return {"bodyText": "완료", "spinnerCount": 0}

    async def wait_for_timeout(self, _milliseconds: int):
        return None


def test_shared_idle_gate_accepts_only_a_quiet_canvas() -> None:
    assert asyncio.run(wait_for_canvas_idle(_IdlePage(), timeout_sec=0.1, poll_ms=1))
