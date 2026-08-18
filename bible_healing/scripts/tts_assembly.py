# -*- coding: utf-8 -*-
"""Assembly-stage SuperTonic pacing. Engine silence is not the timeline."""
from __future__ import annotations

DEFAULT_SAME_SPEAKER_GAP = 0.05
DEFAULT_SCENE_GAP = 0.6


def load_assembly_policy(lock: dict | None) -> dict[str, float]:
    tts = (lock or {}).get("tts") or {}
    return {
        "same": float(tts.get("assembly_gap_same_speaker", DEFAULT_SAME_SPEAKER_GAP)),
        "scene": float(tts.get("assembly_gap_scene", DEFAULT_SCENE_GAP)),
    }


def assembly_gap_seconds(
    prev_speaker: str | None,
    speaker: str,
    policy: dict | None = None,
) -> float:
    """Gap inserted *before* `speaker`. First clip has no leading gap."""
    if prev_speaker is None:
        return 0.0
    if isinstance(policy, dict) and "same" in policy:
        same = float(policy.get("same", DEFAULT_SAME_SPEAKER_GAP))
        scene = float(policy.get("scene", DEFAULT_SCENE_GAP))
    else:
        loaded = load_assembly_policy({"tts": policy or {}})
        same, scene = loaded["same"], loaded["scene"]
    if prev_speaker == speaker:
        return same
    return scene

def accumulate_scene_windows(
    durations: list[float],
    scene_gap: float = DEFAULT_SCENE_GAP,
) -> list[tuple[float, float]]:
    """Start/end for each scene WAV after inserting scene_gap between them."""
    windows: list[tuple[float, float]] = []
    cursor = 0.0
    for index, duration in enumerate(durations):
        dur = float(duration)
        if index > 0:
            cursor += float(scene_gap)
        start = cursor
        end = start + max(0.0, dur)
        windows.append((start, end))
        cursor = end
    return windows
