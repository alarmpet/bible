# -*- coding: utf-8 -*-
"""Test postflight release verification and negative control on legacy flawed final."""
from __future__ import annotations

import json
import sys
from pathlib import Path
import pytest

_TEST_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _TEST_DIR.parents[1]
_SCRIPTS_DIR = _PROJECT_ROOT / "human_archive" / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from postflight_release import (
    verify_postflight,
    verify_release_manifest_schema,
    generate_release_manifest_v4,
)


def test_legacy_flawed_final_fails_postflight_as_negative_control():
    legacy_final = _PROJECT_ROOT / "human_archive" / "runs" / "ep01_pompeii_18hours" / "final_pompeii_ep01.mp4"
    if not legacy_final.exists():
        pytest.skip("Legacy final MP4 not present")

    ok, report = verify_postflight(legacy_final, duration_mode="full")
    # Legacy final MUST fail due to non-square SAR, yuvj420p, low loudness, or length mismatch
    assert ok is False
    assert len(report["errors"]) >= 1


def test_pilot_v2_candidate_passes_postflight():
    # Re-render pilot candidate with BT.709 VUI tags
    from render_episode_v2 import render_build
    build_dir = _PROJECT_ROOT / "human_archive" / "runs" / "ep01_pompeii_rebuild_v2" / "pilot-v2-001"
    if not (build_dir / "asset_manifest.json").exists():
        pytest.skip("Pilot v2 asset manifest not yet created")

    candidate_mp4 = render_build(build_dir)
    ok, report = verify_postflight(candidate_mp4, duration_mode="pilot")
    assert ok is True, f"Pilot postflight errors: {report.get('errors')}"


def test_postflight_verifies_historical_v2_manifest_without_gate8_errors():
    historical_manifest = {
        "schema_version": 2,
        "release_schema_version": "HISTORICAL_PRODUCTION_RELEASE",
        "video_sha256": "B" * 64,
        "duration_sec": 1008.0,
    }
    ok, errors = verify_release_manifest_schema(historical_manifest)
    assert ok is True
    assert errors == []


def test_postflight_verifies_v4_manifest_enforces_gate8_invariants():
    valid_v4 = {
        "schema_version": 4,
        "release_schema_version": "OFFICIAL_PRODUCTION_RELEASE_V4",
        "baretip_in_opening_rejected": True,
        "first_frame_visibility_passed": True,
        "motion_diversity_passed": True,
        "parity_difference_sec": 0.025,
        "shots": [
            {"shot_id": "SHOT_001", "editing_effect": "subpixel_push_in", "asset_type": "FLOW_IMAGE"},
            {"shot_id": "SHOT_002", "editing_effect": "subpixel_pan_right", "asset_type": "FLOW_IMAGE"},
        ],
    }
    ok, errors = verify_release_manifest_schema(valid_v4)
    assert ok is True
    assert errors == []


def test_postflight_v4_fails_if_baretip_in_opening():
    flawed_v4 = {
        "schema_version": 4,
        "release_schema_version": "OFFICIAL_PRODUCTION_RELEASE_V4",
        "baretip_in_opening_rejected": False,
        "first_frame_visibility_passed": True,
        "motion_diversity_passed": True,
        "parity_difference_sec": 0.010,
        "shots": [
            {"shot_id": "SHOT_001", "editing_effect": "bare_tip_whiteboard", "asset_type": "BARETIP_VIDEO"},
        ],
    }
    ok, errors = verify_release_manifest_schema(flawed_v4)
    assert ok is False
    assert any("Gate 8.2" in err for err in errors)


def test_generate_release_manifest_v4_creates_valid_record(tmp_path: Path):
    v_file = tmp_path / "video.mp4"
    a_file = tmp_path / "audio.wav"
    v_file.write_bytes(b"dummy video data")
    a_file.write_bytes(b"dummy audio data")

    shots = [{"shot_id": "SHOT_001", "editing_effect": "subpixel_push_in"}]
    manifest = generate_release_manifest_v4(
        video_path=v_file,
        audio_path=a_file,
        shots=shots,
        parity_diff=0.012,
    )
    assert manifest["release_schema_version"] == "OFFICIAL_PRODUCTION_RELEASE_V4"
    assert manifest["baretip_in_opening_rejected"] is True
    assert manifest["first_frame_visibility_passed"] is True
    assert manifest["motion_diversity_passed"] is True
    assert manifest["parity_difference_sec"] == 0.012

