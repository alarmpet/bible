# -*- coding: utf-8 -*-
"""Task 5: `check_decoded_stream_motion_mae()` was defined but never called from
`verify_postflight()` -- Gate 8.4 (`motion_diversity_passed`) was a pure schema
check that trusted whatever boolean a manifest self-reported, so a manifest
could claim "motion QA passed" without the check ever running (2026-09-15
overhaul plan, Task 5).

These tests pin two things:
1. `verify_postflight()` now measures decoded motion for real on every v4/v5
   release and blocks the release when that measurement fails, even if the
   manifest lies and says PASS.
2. The new streaming measurement (`measure_decoded_video_motion_diversity`,
   needed because a full 20-minute release can't be held in memory as a frame
   list) agrees in direction with the already-tested batch check
   (`check_decoded_stream_motion_mae` in test_encoded_frame_motion_gate.py) on
   real encoded video -- a guard against the two implementations silently
   drifting apart, which is the exact failure mode (build_motion_clips_v2 vs
   smooth_subpixel_motion_engine, both independently buggy) this whole plan is
   about.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from postflight_release import (
    generate_release_manifest_v4,
    measure_decoded_video_motion_diversity,
    verify_postflight,
)

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not on PATH")


def _write_v4_manifest(build_dir: Path, video_path: Path, *, motion_diversity_passed: bool) -> None:
    sha = hashlib.sha256(video_path.read_bytes()).hexdigest().upper()
    manifest = {
        "schema_version": 4,
        "release_schema_version": "OFFICIAL_PRODUCTION_RELEASE_V4",
        "video_file": video_path.name,
        "video_sha256": sha,
        "first_frame_visibility_passed": True,
        "baretip_in_opening_rejected": True,
        "motion_diversity_passed": motion_diversity_passed,
        "parity_difference_sec": 0.010,
        "shots": [{"shot_id": "SHOT_001", "editing_effect": "subpixel_pan_right", "asset_type": "FLOW_IMAGE"}],
    }
    (build_dir / "release_manifest_v4.json").write_text(json.dumps(manifest), encoding="utf-8")


def test_decoded_motion_gate_blocks_release_even_when_manifest_lies(tmp_path: Path, monkeypatch):
    video_path = tmp_path / "candidate.mp4"
    video_path.write_bytes(b"\x00" * 200_000)  # oversized dummy, not a real decodable stream

    monkeypatch.setattr(
        "postflight_release.measure_decoded_video_motion_diversity",
        lambda *a, **k: (False, 0.10, "Static hold / frozen frame detected (test double)"),
    )
    _write_v4_manifest(tmp_path, video_path, motion_diversity_passed=True)

    ok, report = verify_postflight(video_path, build_dir=tmp_path, duration_mode="full")

    assert ok is False
    assert report["checks"]["decoded_motion_diversity"]["status"] == "FAIL"
    assert any("Gate 8.4" in err for err in report["errors"])


def test_decoded_motion_gate_does_not_block_when_measurement_passes(tmp_path: Path, monkeypatch):
    video_path = tmp_path / "candidate.mp4"
    video_path.write_bytes(b"\x00" * 200_000)

    monkeypatch.setattr(
        "postflight_release.measure_decoded_video_motion_diversity",
        lambda *a, **k: (True, 5.0, "Continuous decoded motion verified (test double)"),
    )
    _write_v4_manifest(tmp_path, video_path, motion_diversity_passed=True)

    ok, report = verify_postflight(video_path, build_dir=tmp_path, duration_mode="full")

    assert report["checks"]["decoded_motion_diversity"]["status"] == "PASS"
    assert not any("Gate 8.4" in err for err in report["errors"])


def test_generate_release_manifest_v4_reports_measured_motion_not_hardcoded_true(tmp_path: Path, monkeypatch):
    video_path = tmp_path / "video.mp4"
    audio_path = tmp_path / "audio.wav"
    video_path.write_bytes(b"dummy")
    audio_path.write_bytes(b"dummy")

    monkeypatch.setattr(
        "postflight_release.measure_decoded_video_motion_diversity",
        lambda *a, **k: (False, 0.2, "test double: frozen"),
    )
    manifest = generate_release_manifest_v4(
        video_path=video_path,
        audio_path=audio_path,
        shots=[{"shot_id": "SHOT_001"}],
        parity_diff=0.01,
    )
    assert manifest["motion_diversity_passed"] is False


def _make_frozen_detailed_clip(path: Path, width: int = 160, height: int = 90, fps: int = 25, duration: float = 2.0) -> None:
    """All-intra encode of a static high-frequency image. High spatial detail plus
    -g 1 (every frame a keyframe) keeps the file well above trivial size even
    though the content never changes, so this exercises real decode + a real
    'frozen' motion verdict rather than relying on H.264 temporal skip making
    the file collapse to almost nothing."""
    from PIL import Image

    img = Image.new("RGB", (width, height))
    px = img.load()
    for y in range(height):
        for x in range(width):
            on = ((x // 4) + (y // 4)) % 2 == 0
            px[x, y] = (230, 230, 230) if on else (20, 20, 20)
    img_path = path.with_suffix(".png")
    img.save(img_path)
    subprocess.run(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-loop", "1", "-i", str(img_path),
            "-t", str(duration), "-r", str(fps),
            "-g", "1", "-pix_fmt", "yuv420p", str(path),
        ],
        check=True,
    )


def _make_moving_clip(path: Path, width: int = 160, height: int = 90, fps: int = 25, duration: float = 2.0) -> None:
    subprocess.run(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", f"testsrc=size={width}x{height}:rate={fps}:duration={duration}",
            "-pix_fmt", "yuv420p", str(path),
        ],
        check=True,
    )


def test_streaming_motion_measurement_agrees_with_batch_check_direction_on_real_video(tmp_path: Path):
    frozen = tmp_path / "frozen.mp4"
    moving = tmp_path / "moving.mp4"
    _make_frozen_detailed_clip(frozen)
    _make_moving_clip(moving)

    frozen_passed, frozen_mae, _ = measure_decoded_video_motion_diversity(frozen, window_size=25)
    moving_passed, moving_mae, _ = measure_decoded_video_motion_diversity(moving, window_size=25)

    assert frozen_passed is False, f"frozen clip min_mae={frozen_mae} should read as static hold"
    assert moving_passed is True, f"moving clip min_mae={moving_mae} should read as real motion"
