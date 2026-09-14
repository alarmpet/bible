# -*- coding: utf-8 -*-
"""Integration tests for Human Library Rank 2 exact clone pipeline runner."""
from __future__ import annotations

import json
import sys
from pathlib import Path
import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from run_human_library_rank2_exact_clone_pipeline import (
    EP_DIR,
    IMAGES_DIR,
    METADATA_DIR,
    SUBTITLES_DIR,
    AUDIO_DIR,
    CANONICAL_MANIFEST_PATH,
    SUBCUT_PLAN_PATH,
    PLATES_PLAN_PATH,
    ASS_PATH,
    RAW_AUDIO_PATH,
    TARGET_DURATION_SEC,
    TARGET_FRAMES,
    MASTER_AUDIO_SAMPLES,
    EXPECTED_PLATES_COUNT,
    EXPECTED_SUBCUTS_COUNT,
    build_cinema_filtergraph,
    build_master_audio_command,
    resolve_plate_image,
    validate_master_plate_plan,
)
from lib.exact_release_verifier import count_wav_sample_frames, audit_ass_strict


def test_rank2_pipeline_essential_contracts_exist():
    assert IMAGES_DIR.name == "images_2d_master"
    assert CANONICAL_MANIFEST_PATH.exists(), "Canonical timeline manifest missing"
    assert SUBCUT_PLAN_PATH.exists(), "Subcut montage plan missing"
    assert PLATES_PLAN_PATH.exists(), "Master plates plan missing"
    assert ASS_PATH.exists(), "Exact subtitles ASS missing"
    assert RAW_AUDIO_PATH.exists(), "Exact master audio missing"
    assert count_wav_sample_frames(RAW_AUDIO_PATH) == MASTER_AUDIO_SAMPLES


def test_rank2_subcut_plan_contract_frame_count():
    with open(SUBCUT_PLAN_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    cuts = data.get("cuts", [])
    assert len(cuts) == EXPECTED_SUBCUTS_COUNT, f"Expected {EXPECTED_SUBCUTS_COUNT} cuts, got {len(cuts)}"
    assert sum(c["frame_count"] for c in cuts) == TARGET_FRAMES
    assert TARGET_FRAMES == 43200


def test_rank2_missing_ab_plate_fails_closed_instead_of_parent_fallback(tmp_path):
    with pytest.raises(FileNotFoundError, match="SHOT_001_A"):
        resolve_plate_image(
            plate_id="SHOT_001_A",
            parent_shot_id="SHOT_001",
            plates_dir=tmp_path,
            fallback_images_dir=tmp_path,
        )


def test_rank2_clean_profile_does_not_add_branding_inputs():
    extra_inputs, filtergraph = build_cinema_filtergraph(
        ass_subtitles=Path("subtitles.ass"),
        include_branding=False,
    )
    assert extra_inputs == []
    assert "golden_emblem" not in filtergraph
    assert "overlay" not in filtergraph
    assert "ass=" in filtergraph


def test_rank2_audio_command_binds_exact_sample_boundary():
    command = build_master_audio_command(
        original_mp4=Path("original.mp4"),
        output_path=Path("audio.wav"),
        sample_count=69_120_000,
    )
    command_text = " ".join(command)
    assert "-frames:a 69120000" in command_text
    assert "-t 1440" not in command_text


def test_rank2_master_plate_plan_validation_is_fail_closed(tmp_path):
    plan = tmp_path / "plates.json"
    plan.write_text(json.dumps({"plates": [{"plate_id": "SHOT_001_A"}]}), encoding="utf-8")

    result = validate_master_plate_plan(plan, expected_count=1)
    assert result["status"] == "FAIL"
