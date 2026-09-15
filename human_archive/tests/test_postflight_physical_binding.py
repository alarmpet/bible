# -*- coding: utf-8 -*-
from __future__ import annotations
import json
import shutil
from pathlib import Path
import pytest

from postflight_release import verify_postflight, verify_release_manifest_schema

def test_corrupted_video_byte_fails_postflight_manifest_verification(tmp_path: Path):
    # Create valid synthetic video and manifest
    video_file = tmp_path / "test_video.mp4"
    # Create minimal mp4 or dummy file
    video_file.write_bytes(b"VALID_VIDEO_CONTENT_ORIGINAL" * 100)
    
    manifest_file = tmp_path / "release_manifest_v4.json"
    import hashlib
    h = hashlib.sha256(video_file.read_bytes()).hexdigest().upper()
    
    manifest_data = {
        "schema_version": 4,
        "release_schema_version": "OFFICIAL_PRODUCTION_RELEASE_V4",
        "video_file": video_file.name,
        "video_sha256": h,
        "audio_file": "audio.wav",
        "audio_sha256": "A" * 64,
        "first_frame_visibility_passed": True,
        "baretip_in_opening_rejected": True,
        "motion_diversity_passed": True,
        "parity_difference_sec": 0.015,
        "shots": [{"shot_id": "SHOT_001", "editing_effect": "pan_right", "asset_type": "FLOW_IMAGE"}],
    }
    manifest_file.write_text(json.dumps(manifest_data), encoding="utf-8")
    
    # Tamper with 1 byte of video_file
    video_file.write_bytes(b"CORRUPTED_VIDEO_BYTE_MODIFIED" * 100)
    
    ok, report = verify_postflight(video_file, build_dir=tmp_path, duration_mode="pilot")
    assert ok is False
    assert any("sha256" in err.lower() or "mismatch" in err.lower() for err in report.get("errors", []))
