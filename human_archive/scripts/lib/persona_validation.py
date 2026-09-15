# -*- coding: utf-8 -*-
"""Persona and 5-stage story beat validation library for ShipSeonbi."""
from __future__ import annotations

import json
from typing import Any


def validate_persona(
    script: dict[str, Any],
    policy: dict[str, Any],
    audio_manifest: object | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    persona = script.get("persona", "standard")
    sentences = script.get("sentences", [])

    story_cfg = policy.get("story", {})
    voice_cfg = policy.get("voice", {})
    req_beats = story_cfg.get("required_beats", [])

    # 1. Beat checks
    found_beats = [s.get("beat") for s in sentences if s.get("beat")]
    found_beat_set = set(found_beats)

    for rb in req_beats:
        if rb not in found_beat_set:
            errors.append(f"missing beat: {rb}")

    # 2. Signature hook checks
    sig_hook = voice_cfg.get("signature_hook", "허허, 천만의 말씀!")
    sig_count = sum(s.get("display_text", "").count(sig_hook) for s in sentences)
    min_sig = voice_cfg.get("signature_hook_min", 1)
    max_sig = voice_cfg.get("signature_hook_max", 1)

    if sig_count < min_sig:
        errors.append(f"Signature hook '{sig_hook}' missing (count={sig_count})")
    elif sig_count > max_sig:
        errors.append(f"Signature hook '{sig_hook}' overused (count={sig_count} > {max_sig})")

    # 3. Prohibited patterns
    prohib = voice_cfg.get("prohibited_patterns", [])
    for s in sentences:
        txt = s.get("display_text", "")
        for p in prohib:
            if p in txt:
                errors.append(f"Prohibited pattern '{p}' found in sentence {s.get('sentence_id')}")

        max_chars = voice_cfg.get("sentence_max_chars", 65)
        if len(txt) > max_chars:
            errors.append(f"Sentence {s.get('sentence_id')} exceeds max characters ({len(txt)} > {max_chars})")

    # 4. Timing checks
    timing_status = "PASS"
    timing_checks: dict[str, Any] = {}
    hook_max = story_cfg.get("hook_end_sec_max", 15.0)
    roadmap_max = story_cfg.get("roadmap_end_sec_max", 45.0)
    if hook_max is not None:
        timing_checks["hook_end_sec_max"] = hook_max
    if roadmap_max is not None:
        timing_checks["roadmap_end_sec_max"] = roadmap_max

    timing_review_required = False
    timing_ends: dict[str, float | int] = {}
    if audio_manifest is None:
        timing_review_required = True
    elif not isinstance(audio_manifest, dict):
        timing_review_required = True
    else:
        if "sentences" in audio_manifest:
            raw_rows = audio_manifest.get("sentences")
            id_key = "sentence_id"
            end_key = "end_sec"
        else:
            raw_rows = audio_manifest.get("shots", [])
            id_key = "shot_id"
            end_key = "endSeconds"

        if not isinstance(raw_rows, list):
            timing_review_required = True
        else:
            for row in raw_rows:
                if not isinstance(row, dict):
                    timing_review_required = True
                    continue
                row_id = row.get(id_key)
                row_end = row.get(end_key)
                if (
                    not isinstance(row_id, str)
                    or not row_id
                    or not isinstance(row_end, (int, float))
                    or isinstance(row_end, bool)
                ):
                    timing_review_required = True
                    continue
                timing_ends[row_id] = row_end
            if not timing_ends:
                timing_review_required = True

    hook_s = next((s for s in reversed(sentences) if s.get("beat") == "hook"), None)
    roadmap_s = next((s for s in reversed(sentences) if s.get("beat") == "roadmap"), None)
    if hook_s is None or roadmap_s is None:
        timing_review_required = True
    else:
        hook_end = timing_ends.get(hook_s.get("sentence_id"))
        roadmap_end = timing_ends.get(roadmap_s.get("sentence_id"))
        if hook_end is None:
            timing_review_required = True
        else:
            timing_checks["hook_end_sec"] = hook_end
            if hook_max is not None and hook_end > hook_max:
                errors.append(f"Hook exceeded max time ({hook_end}s > {hook_max}s)")
                timing_status = "FAIL"
        if roadmap_end is None:
            timing_review_required = True
        else:
            timing_checks["roadmap_end_sec"] = roadmap_end
            if roadmap_max is not None and roadmap_end > roadmap_max:
                errors.append(f"Roadmap exceeded max time ({roadmap_end}s > {roadmap_max}s)")
                timing_status = "FAIL"

    if timing_status != "FAIL" and timing_review_required:
        timing_status = "REVIEW_REQUIRED"

    overall_status = "FAIL" if errors else ("REVIEW_REQUIRED" if timing_status == "REVIEW_REQUIRED" else "PASS")

    return {
        "schema_version": 1,
        "persona": persona,
        "overall_status": overall_status,
        "timing_status": timing_status,
        "timing_checks": timing_checks,
        "errors": errors,
        "beat_checks": {"found_beats": found_beats, "required_beats": req_beats},
        "voice_checks": {"signature_count": sig_count, "prohibited_count": 0},
    }
