# -*- coding: utf-8 -*-
"""Deterministic QA helpers for the first-minute hook."""
from __future__ import annotations

import re
from typing import Any

HOOK_PHASES = {"hook", "mirror", "validate", "permission_bridge", None}
FORBIDDEN_FIRST_MINUTE = (
    r"반드시\s*잠들",
    r"치유(?:됩니다|된다|할\s*수)",
    r"불안이\s*사라",
    r"수면을?\s*보장",
)
OPTIONAL_BREATHING = ("편하다면", "가능하다면", "괜찮다면", "원한다면")


def _scene_meta(scene: dict[str, Any]) -> dict[str, Any]:
    return scene.get("meta") or {}


def summarize_first_minute(
    manifest: dict[str, Any], scenes: list[dict[str, Any]]
) -> dict[str, Any]:
    """Return first-minute measurements and violations from locked timing data."""
    scene_by_order = {int(scene["order"]): scene for scene in scenes}
    items = sorted(manifest.get("scenes") or [], key=lambda item: int(item["order"]))
    if not items:
        raise ValueError("manifest has no scenes")

    for scene in scenes:
        phase = _scene_meta(scene).get("hook_phase")
        if phase not in HOOK_PHASES:
            raise ValueError(f"unknown hook_phase: {phase}")

    first_voice_start = min(float(item["startSeconds"]) for item in items)
    first_scripture_start = None
    first_minute_text: list[str] = []
    phases: list[str] = []
    for item in items:
        scene = scene_by_order.get(int(item["order"]), {})
        meta = _scene_meta(scene)
        if meta.get("speaker") == "scripture" and first_scripture_start is None:
            first_scripture_start = float(item["startSeconds"])
        if float(item["startSeconds"]) < 60.0:
            first_minute_text.append(scene.get("narration") or "")
            phase = meta.get("hook_phase")
            if phase:
                phases.append(phase)

    text = " ".join(first_minute_text)
    violations: list[str] = []
    if first_voice_start > 0.5:
        violations.append("voice_starts_after_0_5_sec")
    if first_scripture_start is None:
        violations.append("missing_first_scripture")
    elif not 45.0 <= first_scripture_start <= 55.0:
        violations.append("first_scripture_outside_45_55_sec")
    if any(re.search(pattern, text) for pattern in FORBIDDEN_FIRST_MINUTE):
        violations.append("forbidden_claim_in_first_minute")
    if re.search(r"(?:숨|호흡).{0,20}(?:쉬세요|하세요|들이쉬|내쉬)", text):
        if not any(token in text for token in OPTIONAL_BREATHING):
            violations.append("breathing_instruction_not_optional")

    return {
        "first_voice_start_sec": first_voice_start,
        "first_scripture_start_sec": first_scripture_start,
        "first_scripture_in_target_window": (
            first_scripture_start is not None
            and 45.0 <= first_scripture_start <= 55.0
        ),
        "phases": phases,
        "violations": violations,
    }
