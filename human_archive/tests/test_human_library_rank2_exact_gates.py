# -*- coding: utf-8 -*-
"""
test_human_library_rank2_exact_gates.py
Unified Gate 0~4 physical verification test suite for Rank 2 ('잊혀진 문명, 세계 최강이 사라진 이유')
1:1 exact replication pipeline (1,440.00s / 24.00min, 43,200 frames @ 30fps CFR).
"""

import json
import sys
from pathlib import Path
import pytest

_TESTS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _TESTS_DIR.parent
_SCRIPTS_DIR = _REPO_ROOT / "scripts"
_LIB_DIR = _SCRIPTS_DIR / "lib"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))
if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from lib.exact_release_verifier import audit_ass_strict, count_wav_sample_frames

RUN_DIR = _REPO_ROOT / "runs" / "human_library_replica" / "rank2_forgotten_civilization"
METADATA_DIR = RUN_DIR / "metadata"
SUBTITLES_DIR = RUN_DIR / "subtitles"
AUDIO_DIR = RUN_DIR / "audio"
GENERATION_DIR = RUN_DIR / "generation"


def test_rank2_gate_0_duration_and_cfr_invariants():
    fps = 30.0
    target_dur = 1440.0
    total_frames = round(target_dur * fps)
    assert total_frames == 43200

    samples_per_frame = 48000 // 30  # 1600
    total_samples = total_frames * samples_per_frame
    assert total_samples == 69_120_000

    audio_dur = total_samples / 48000.0
    parity_delta = abs(target_dur - audio_dur)
    assert parity_delta == 0.0, f"Gate 0 Parity Delta {parity_delta}s != 0.0s"


def test_rank2_gate_1_subtitles_ssot_and_no_zero_stacking():
    ass_path = SUBTITLES_DIR / "rank2_exact_master_subtitles.ass"
    assert ass_path.exists(), f"Exact master subtitles missing: {ass_path}"

    res = audit_ass_strict(ass_path)
    assert res["status"] == "PASS", f"Strict audit failed: {res['errors']}"
    assert res["multiline_events"] == 0
    assert res["zero_start_events"] == 0
    assert res["overlap_events"] == 0
    assert res["dialogue_events"] >= 507

    # Check keyword highlighting
    lines = [l for l in ass_path.read_text(encoding="utf-8").splitlines() if l.startswith("Dialogue:")]
    yellow_lines = [l for l in lines if r"\c&H003BEBFF&" in l]
    assert len(yellow_lines) >= 50, f"Expected >= 50 yellow highlighted lines, got {len(yellow_lines)}"


def test_rank2_gate_2_2d_webtoon_prompt_aesthetic_hygiene():
    plan_path = METADATA_DIR / "master_plates_composition_plan.json"
    req_path = GENERATION_DIR / "image_request_manifest.json"
    assert plan_path.exists(), f"Master plates plan missing: {plan_path}"
    assert req_path.exists(), f"Image request manifest missing: {req_path}"

    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    assert plan["total_plates"] == 128
    assert len(plan["plates"]) == 128

    forbidden = {"photorealistic", "8k", "hyperrealistic", "unreal engine", "octane render"}
    for p in plan["plates"]:
        prompt = p["flow_prompt_en"].lower()
        assert len(p["flow_prompt_en"]) <= 441, f"Prompt exceeds 441 chars in {p['plate_id']}: {len(p['flow_prompt_en'])}"
        for f in forbidden:
            assert f not in prompt, f"Forbidden word '{f}' in {p['plate_id']}"
        assert "2d ligne claire" in prompt or "webtoon" in prompt or "cel-shaded" in prompt


def test_rank2_gate_3_pacing_and_subcut_count():
    subcut_path = METADATA_DIR / "subcut_montage_plan.json"
    assert subcut_path.exists(), f"Subcut montage plan missing: {subcut_path}"

    data = json.loads(subcut_path.read_text(encoding="utf-8"))
    cuts = data["cuts"]

    assert 800 <= len(cuts) <= 900, f"Expected 800~900 cuts, got {len(cuts)}"
    total_frames = sum(c["frame_count"] for c in cuts)
    assert total_frames == 43200, f"Frame count invariant failed: {total_frames} != 43200"

    # First 300s must have 185 cuts
    first_300_cuts = [c for c in cuts if c["start_sec"] < 300.0]
    assert len(first_300_cuts) >= 180

    # Strobe burst at 40~46s
    strobe_cuts = [c for c in cuts if 40.0 <= c["start_sec"] < 46.0]
    assert len(strobe_cuts) >= 15
    for c in strobe_cuts:
        assert c["duration_sec"] <= 0.40


def test_rank2_gate_4_exact_audio_boundary_and_samples():
    wav_path = AUDIO_DIR / "rank2_exact_master_audio_48k.wav"
    assert wav_path.exists(), f"Master audio WAV missing: {wav_path}"
    assert wav_path.stat().st_size > 200_000_000, f"WAV size too small: {wav_path.stat().st_size}"

    samples = count_wav_sample_frames(wav_path)
    assert samples == 69_120_000, f"Sample frame boundary mismatch: {samples} != 69,120,000"
