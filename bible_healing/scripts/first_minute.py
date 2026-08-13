# -*- coding: utf-8 -*-
"""Deterministic QA helpers for the first-minute hook."""
from __future__ import annotations
import re
from typing import Any

HOOK_PHASES = {"hook", "mirror", "validate", "permission_bridge", None}
FORBIDDEN_FIRST_MINUTE = (r"반드시\s*잠들", r"치유(?:됩니다|된다|될 거예요)", r"불안이\s*사라", r"수면\s*보장")
OPTIONAL_BREATHING = ("편하다면", "가능하다면", "괜찮다면", "원한다면")


def _scene_meta(scene: dict[str, Any]) -> dict[str, Any]:
    return scene.get("meta") or {}


def _timed_items(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    rows = manifest.get("scenes") or manifest.get("items") or []
    rows = sorted(rows, key=lambda row: int(row.get("order", 0)))
    timed, cursor = [], 0.0
    for index, item in enumerate(rows, 1):
        duration = float(item.get("duration") or item.get("durationSeconds") or item.get("measuredDurationSeconds") or 0.0)
        start = item.get("startSeconds", item.get("startSec"))
        start_value = float(start) if start is not None else cursor
        timed.append({**item, "order": int(item.get("order", index)), "startSeconds": start_value, "duration": duration})
        cursor = start_value + duration
    return timed


def summarize_first_minute(manifest: dict[str, Any], scenes: list[dict[str, Any]]) -> dict[str, Any]:
    scene_by_order = {int(scene.get("order", index)): scene for index, scene in enumerate(scenes, 1)}
    items = _timed_items(manifest)
    if not items:
        raise ValueError("manifest has no scenes")
    for scene in scenes:
        phase = _scene_meta(scene).get("hook_phase")
        if phase not in HOOK_PHASES:
            raise ValueError(f"unknown hook_phase: {phase}")
    first_voice_start = min(float(item["startSeconds"]) for item in items)
    first_scripture_start = None
    first_minute_text, phases = [], []
    for item in items:
        scene = scene_by_order.get(int(item["order"]), {})
        meta = _scene_meta(scene)
        if (meta.get("speaker") or scene.get("speaker")) == "scripture" and first_scripture_start is None:
            first_scripture_start = float(item["startSeconds"])
        if float(item["startSeconds"]) < 60.0:
            first_minute_text.append(scene.get("narration") or scene.get("text") or "")
            if meta.get("hook_phase"):
                phases.append(meta["hook_phase"])
    text = " ".join(first_minute_text)
    violations = []
    if first_voice_start > 0.5:
        violations.append("voice_starts_after_0_5_sec")
    if first_scripture_start is None:
        violations.append("missing_first_scripture")
    elif not 45.0 <= first_scripture_start <= 55.0:
        violations.append("first_scripture_outside_45_55_sec")
    if any(re.search(pattern, text) for pattern in FORBIDDEN_FIRST_MINUTE):
        violations.append("forbidden_claim_in_first_minute")
    if re.search(r"(?:숨|호흡|어깨).{0,20}(?:내려놓|쉬|들이마)", text) and not any(token in text for token in OPTIONAL_BREATHING):
        violations.append("breathing_instruction_not_optional")
    return {"first_voice_start_sec": first_voice_start, "first_scripture_start_sec": first_scripture_start, "first_scripture_in_target_window": first_scripture_start is not None and 45.0 <= first_scripture_start <= 55.0, "phases": phases, "violations": violations}
